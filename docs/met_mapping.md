# GYMFIT 2024 Adult Compendium MET mapping

The 43 catalog exercises are mapped to the nearest Compendium activity class, not
treated as 43 independently measured activities. `MODERATE` is the application
default. Cardio equipment uses an intensity-band default because speed, watts and
resistance are not currently captured.

| GYMFIT exercises | LOW | MODERATE | HIGH | Compendium code basis |
|---|---:|---:|---:|---|
| LEG_PRESS, LEG_EXTENSION, LEG_CURL, HIP_THRUST, CALF_RAISE, BENCH_PRESS, INCLINE_BENCH_PRESS, DUMBBELL_PRESS, CHEST_PRESS, CABLE_FLY, PEC_DECK_FLY, LAT_PULLDOWN, SEATED_ROW, BARBELL_ROW, ONE_ARM_DUMBBELL_ROW, SHOULDER_PRESS, LATERAL_RAISE, FRONT_RAISE, REAR_DELT_FLY, FACE_PULL, BARBELL_CURL, DUMBBELL_CURL, HAMMER_CURL, TRICEPS_PUSHDOWN, OVERHEAD_TRICEPS_EXTENSION | 3.5 | 3.5 | 6.0 | 02054 / 02050 |
| SQUAT, ROMANIAN_DEADLIFT, DEADLIFT | 3.5 | 5.0 | 6.0 | 02054 / 02052 / 02050 |
| PUSHUP, LUNGE, BULGARIAN_SPLIT_SQUAT, PULLUP, DIPS, LEG_RAISE, RUSSIAN_TWIST, MOUNTAIN_CLIMBER | 3.0 | 3.8 | 6.5 | 02056 / 02022 / 02057 |
| PLANK, CRUNCH | 2.8 | 3.0 | 6.5 | 02024 / 02056 / 02057 |
| TREADMILL | 3.5 | 4.8 | 9.0 | 17352 / 17358 / 12045 |
| STATIONARY_BIKE | 4.0 | 6.0 | 9.0 | 01214 / 01220 / 01270 |
| STEPMILL | 4.5 | 9.3 | 9.3 | 17133 / 02065 / 17134 |
| ELLIPTICAL | 5.0 | 5.0 | 9.0 | 02048 / 02049 |
| ROWING_MACHINE | 5.0 | 5.0 | 7.3 | 02071 / 02070 |

Source: 2024 Adult Compendium of Physical Activities,
https://pacompendium.com/adult-compendium/

`training_volume_kg` uses `weight_kg × repetition_count`. In the current coaching
record, `repetition_count` is already the total of completed repetitions across all
sets, so multiplying by `completed_sets` again would double-count volume. For future
set-varying weights, sum each completed set's `weight_kg × repetitions`.
