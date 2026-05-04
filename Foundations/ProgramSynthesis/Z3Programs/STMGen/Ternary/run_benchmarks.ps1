# Ternary benchmark commands.
# Run from STMGen/ directory. Settings shared across all runs:
#   not_always_extract = ON, constant_synthesis = OFF
# Field minimisation is the only knob: ON vs OFF (toggle --field_min).
# Output is piped to the similarly-named .p4 file (suffix _min / _nomin).

# 1) single_if_else  (extract field0; ternary on (field0.v & 5); accept/reject)
python runner.py --input Ternary/single_if_else.parser --not_always_extract ON --constant_synthesis OFF --field_min ON  --max_states 5 --max_entries 5 --output Ternary/single_if_else_min.p4
python runner.py --input Ternary/single_if_else.parser --not_always_extract ON --constant_synthesis OFF --field_min OFF --max_states 5 --max_entries 5 --output Ternary/single_if_else_nomin.p4

# 2) multiple_if  (extract h; three (h.v & 7) ternary arms each extracting a/b/c; reject default)
python runner.py --input Ternary/multiple_if.parser --not_always_extract ON --constant_synthesis OFF --field_min ON  --max_states 5 --max_entries 5 --output Ternary/multiple_if_min.p4
python runner.py --input Ternary/multiple_if.parser --not_always_extract ON --constant_synthesis OFF --field_min OFF --max_states 5 --max_entries 5 --output Ternary/multiple_if_nomin.p4

# 3) check_after_extract  (extract hdr1, hdr2; (hdr1.f0 & 11)==10 or hdr1.f0==15 -> hdr3; accept)
python runner.py --input Ternary/check_after_extract.parser --not_always_extract ON --constant_synthesis OFF --field_min ON  --max_states 6 --max_entries 5 --output Ternary/check_after_extract_min.p4
python runner.py --input Ternary/check_after_extract.parser --not_always_extract ON --constant_synthesis OFF --field_min OFF --max_states 6 --max_entries 5 --output Ternary/check_after_extract_nomin.p4

# 4) nested_if_else2  (extract h0; (h0.f0 & 6)==4 -> h1; nested (& 15)==12 / (& 3)==3 dispatch -> h2 / h3; accept)
python runner.py --input Ternary/nested_if_else2.parser --not_always_extract ON --constant_synthesis OFF --field_min ON  --max_states 6 --max_entries 5 --output Ternary/nested_if_else2_min.p4
python runner.py --input Ternary/nested_if_else2.parser --not_always_extract ON --constant_synthesis OFF --field_min OFF --max_states 6 --max_entries 5 --output Ternary/nested_if_else2_nomin.p4

# 5) nested_if_else1  (extract struct1; nested struct2/3/4 + struct5; accept). Larger search space — slowest.
python runner.py --input Ternary/nested_if_else1.parser --not_always_extract ON --constant_synthesis OFF --field_min ON  --max_states 8 --max_entries 6 --output Ternary/nested_if_else1_min.p4
python runner.py --input Ternary/nested_if_else1.parser --not_always_extract ON --constant_synthesis OFF --field_min OFF --max_states 8 --max_entries 6 --output Ternary/nested_if_else1_nomin.p4
