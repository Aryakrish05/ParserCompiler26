# ParserCompiler26

Synthesise a hardware-friendly P4 parser from sequential C-like packet-parsing
code. The compiler models the input as a finite-state machine (FSM), runs a
Counterexample-Guided Inductive Synthesis (CEGIS) loop on top of the Z3 SMT
solver, and emits a tabular FSM whose accept/reject verdict and sequence of
extracted headers match the input program on every possible packet. The output
is valid P4 code accepted by `p4c`.

This is the implementation accompanying my UGRC report at IIT Madras
(CS4900). The full report is in [`Report/`](Report/); the slides are in
[`Presentation/`](Presentation/).

## Motivation

Packet processing today is written either in C (for software dataplanes) or
in P4 (for programmable hardware). Parsers in P4 map directly to FSMs. In C
the control flow encodes a parser implicitly, which is convenient to write
but harder to target at hardware and harder to reason about under
control-flow divergence. Lifting the C-like code to an FSM automatically
gives both a hardware-targetable representation and a cleaner foundation
for further analyses.

## DSL

A program is stored in a `.parser` file. The DSL is a restricted subset of C:
struct declarations, an anonymous `phv` struct that names the headers,
`Extract(phv.<header>)` calls, `if`/`else if` with exact (`field == const`)
or ternary (`(field & mask) == value`) conditions, and
`return ACCEPT`/`return REJECT`. Loops, lookaheads, `&&`/`||`, function calls
and variable-length fields are not supported.

```c
struct ethernet_t { bit_48 dst; bit_48 src; bit_16 ether_type; };
struct ipv4_t { /* fields */ };
struct arp_t  { /* fields */ };

struct {
    ethernet_t ethernet;
    ipv4_t     ipv4;
    arp_t      arp;
} phv;

int parse() {
    Extract(phv.ethernet);
    if (phv.ethernet.ether_type == 0x0800) {
        Extract(phv.ipv4);
        return ACCEPT;
    } else if (phv.ethernet.ether_type == 0x0806) {
        Extract(phv.arp);
        return REJECT;
    }
    return ACCEPT;
}
```

## Pipeline

Four stages, each with a small number of modules.

- **Frontend** (`frontend/`)
  - `Analyser` collects information about each struct, the members of `phv`
    and the fields of each member, and rejects malformed input.
  - `FieldMinimiser` shrinks field widths by renumbering exact-match
    constants and dropping uncompared members where it is safe to do so.
  - `IRGenerator` emits the program as a `.pc` file: an intermediate form
    without structs, with each field width embedded in its `Extract` call.

- **Specification construction** (`spec/`)
  - `CFGBuilder` constructs a CFG for the `.pc` IR and rejects programs
    that extract a field twice on a path or branch on a field before
    extracting it.
  - `SpecBuilder` walks the CFG and produces a Z3 logical specification: a
    list of bit-vector expressions for the extracted fields and a Boolean
    expression for the final accept/reject verdict.

- **Synthesis** (`synthesis/`)
  - `STMSynthesiser` runs the CEGIS loop. The Generator proposes candidate
    FSMs and the Verifier searches for counterexample packets. The FSM is
    constrained to a tabular form: each state has a default field, a
    default next state, and a list of transition entries
    `(state, match_value, next_state)`. Two designs are supported (Section
    3.5 of the report).

- **Backend** (`backend/`)
  - `FieldRestorer` undoes the `FieldMinimiser`'s remapping so the FSM
    refers to the original fields and constants.
  - `P4Generator` emits the final P4 code from the restored FSM.
  - `drop_and_stitch` is the optimisation from Section 3.6.3 — drop
    uncompared headers before synthesis and stitch them back into the FSM
    afterwards.

## Running

```
python runner.py --input <path/to/file.parser> --output <out.p4> [flags]
```

Flags (all `ON`/`OFF`):

- `--not_always_extract` — Design 1 vs Design 2.
- `--constant_synthesis` — restrict synthesised match values to source
  constants.
- `--field_min` — toggle `FieldMinimiser`.
- `--drop_uncompared` — apply the drop-and-stitch optimisation.

`max_states` and `max_entries` cap the table-size / state-count search.

`inspect_parser.py` prints the logical spec, the CFG and the synthesised
state-machine table for a given `.parser` file.

The PowerShell scripts under `scripts/` reproduce the benchmark sweeps
discussed in Section 4 of the report.

## Evaluation highlights

Full evaluation is in Chapter 4 of the report. A few headline numbers:

- `FieldMinimiser` cuts the total PHV width across compared/uncompared
  fields by an order of magnitude or more on the larger benchmarks
  (`nested_if_else1`: 104 → 11 bits; `multiple_if`: 72 → 5 bits on the
  exact benchmarks).
- The same optimisation flips `nested_if_else1` from a 20-minute timeout
  to a ~10-minute completion under Design 2.
- Constant synthesis gives a smaller but consistent speedup, most visible
  on the `single_if_elif_else` runs.

## Limitations and future work

The DSL covers a useful subset of real parsers but excludes loops,
arbitrary conditions, lookahead, function calls and variable-length
fields. Byte-order of header constants is currently treated as the parser
sees it, without an explicit endian conversion step. Ternary handling
could be improved by a more principled treatment of overlapping masks.
Chapter 5 of the report discusses these in detail.

## Repository layout

```
runner.py             entry point
inspect_parser.py     pretty-printer for spec / CFG / STM table

frontend/             Analyser, FieldMinimiser, IRGenerator
spec/                 CFGBuilder, SpecBuilder
synthesis/            STMSynthesiser
backend/              FieldRestorer, P4Generator, drop-and-stitch
viz/                  parse-graph rendering

benchmarks/
    exact/            programs that use only exact comparisons
    ternary/          programs that use ternary comparisons
    realistic/        translated parsers from ParserHawk and similar sources
examples/             illustrative programs used in the report
scripts/              PowerShell sweep scripts
motivation/           early design notes, prototype tests, and one-off probes
_build/               IR (.pc) and other intermediate artefacts (gitignored)

Report/               full UGRC report (LaTeX sources)
Presentation/         slide deck (LaTeX sources)
Foundations/          early Z3 tutorials and exploratory CEGIS prototypes
```

## Reference

The ParserHawk paper (SIGCOMM 2025) is the closest related work and
inspired the synthesis encoding used here. Z3 documentation and CEGIS
references are listed in [`Report/references.bib`](Report/references.bib).
