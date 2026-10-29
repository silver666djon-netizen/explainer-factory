# Release checks (CI build)

| check | long | s1 | s2 | s3 | s4 | s5 | s6 | s7 |
|---|---|---|---|---|---|---|---|---|
| plate_fit | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| crop_fit | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| jitter_check | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| mark_in_frame | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| mark_on_object | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| hand_over_ink | FAIL (2) | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| shorts_picture_size | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| shorts_length | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| count_up | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| sfx_sync | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| voice_cut_check | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| text_stability | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

- long · hand_over_ink: 4:16.6 hand covers 100% of the ink of '+ $18'
- long · hand_over_ink: 4:17.1 hand covers 100% of the ink of 'FEES'

## Check self-test (R40)

| check_selftest | planted bug | result |
|---|---|---|
| plate_fit | source plate wider than the frame (runs off both edges) | FAIL |
| crop_fit | Short: a mark moved out of the beat's window | FAIL |
| jitter_check | a mark shaking +-1.5 px frame to frame | FAIL |
| mark_in_frame | a picture mark pushed off the right edge | FAIL |
| mark_on_object | a stub mark moved off the ticket | FAIL |
| hand_over_ink | the left (mirrored) hand of r86 over the letters it wrote | FAIL |
| shorts_picture_size | Short picture band at 30 % of the frame height | FAIL |
| shorts_length | a 50 s Short | FAIL |
| count_up | a 1.4 s count-up | FAIL |
| sfx_sync | a 0.5 s scratch with no ink being laid | FAIL |
| voice_cut_check | an edit point in the middle of a word | FAIL |
| text_stability | kinetic words re-centring halfway through the card | FAIL |
