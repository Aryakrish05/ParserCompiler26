#Verifier probe: take the broken 5/2 STM that runner.py "verified" for
#single_if_elif_else under NAE=ON CS=OFF FM=ON, manually instantiate the
#STMVerifier, and ask Z3 whether a counterexample exists. Compare to the
#hand-derived counterexample (packet with f0_reduced=3 -> spec says hdr3,
#STM says hdr1).

from specgen import get_spec
from genparser import STMVerifier
from z3 import set_param

set_param('verbose', 0)

info, entry, max_packet_size, default_phv, spec, constants, mask_constants, \
    ternary_match, max_field_size, is_straight_line = get_spec(
        "Exact/single_if_elif_else.parser",
        drop_uncompared=False,
        field_min=True,
    )

selected = info.all_field_nos
no_fields = len(selected)
field_sizes = [None]*no_fields
field_names = [None]*no_fields
for attr,fno in selected.items():
    field_sizes[fno] = info.get_new_size(attr)
    field_names[fno] = info.get_cmpname(attr)

print("field_sizes =", field_sizes)
print("field_names =", field_names)
print("max_packet_size =", max_packet_size)
print("max_field_size =", max_field_size)

#The synth's reported STM (from Exact/single_if_elif_else.p4):
#  start (state 0): default_field = hdr0, default_next = state_2 (=2)
#  state_1 (state 1): default_field = hdr3, default_next = state_4 (=4)  [unreachable]
#  state_2 (state 2): default_field = hdr1, default_next = state_4 (=4)
#  state_3 (state 3): default_field = hdr2, default_next = state_4 (=4)
#  state_4 (state 4): default_field = tail, default_next = accept (=5)
#  Entry: state=0, value=2 (= old 400 after FM remap), next_state=3
hdr0 = selected[("hdr0","f0")]
hdr1 = selected[("hdr1","f1")]
hdr2 = selected[("hdr2","f1")]
hdr3 = selected[("hdr3","f1")]
tail = selected[("tail","f0")]
print("indices:", dict(hdr0=hdr0, hdr1=hdr1, hdr2=hdr2, hdr3=hdr3, tail=tail))

#The .p4 emits "400 -> state_3" via get_old_constant(reduced_value).
#Reverse via get_new_constant to figure out what the synth's reduced entry was.
entry_val_for_400 = info.get_new_constant(("hdr0","f0"), 400)
print("synth entry value for old 400 =", entry_val_for_400)

table_entries = [(0, 3, entry_val_for_400)]   #(entry_state, entry_next_state, entry_match_value)
default_field      = [hdr0, hdr3, hdr1, hdr2, tail]
default_next_state = [2,    4,    4,    4,    5]

no_states = len(default_field)
v = STMVerifier(table_entries, default_field, default_next_state,
                no_fields, max_packet_size, max_field_size,
                ternary_match=False, not_always_extract=True)
v.add_verification_constraint(field_sizes, default_phv, no_states, spec)

print("verifier sat?", v.is_sat())
if v.is_sat():
    cex = v.get_counterexample()
    print("counterexample packet =", cex)
    cex_int = cex.as_long()

    #Print spec output and synth output on this exact packet so we can see
    #which field/state the verifier flagged.
    from z3 import BitVecVal, simplify
    pkt_const = BitVecVal(cex_int, max_packet_size)

    desired_phv, desired_acc = spec(pkt_const)
    print("\nspec on counterexample:")
    for fno, name in enumerate(field_names):
        print(f"  {name:<14} = {simplify(desired_phv[fno])}")
    print(f"  accept_or_reject  = {simplify(desired_acc)}")

    final_state, _, final_phv = v.simulate_stm(field_sizes, default_phv, pkt_const, no_states)
    print("\nsynth STM on counterexample:")
    for fno, name in enumerate(field_names):
        print(f"  {name:<14} = {simplify(final_phv[fno])}")
    print(f"  final_state       = {simplify(final_state)}")
