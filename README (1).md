# System Models - BLG345E Term Project Phase 1

Five concurrent and reactive systems modeled as finite transition systems. Each system is provided in two independent representations that describe the same behavior:

- a JSON Kripke structure following the standardized project schema (`atomic_propositions`, `initial_states`, `states` with `labels` and `transitions`)
- a NuSMV model (`.smv`)

## Files

| System | JSON | NuSMV | Atomic propositions |
|--------|------|-------|---------------------|
| Dining Philosophers (3 philosophers, 3 forks) | `models/philosophers.json` | `models/philosophers.smv` | `P0_eating`, `P1_eating`, `P2_eating`, `deadlock` |
| Peterson's mutual exclusion (2 processes) | `models/peterson.json` | `models/peterson.smv` | `P0_in_CS`, `P1_in_CS`, `flag0`, `flag1`, `turn_is_1` |
| Alternating Bit Protocol | `models/abp.json` | `models/abp.smv` | `packet_lost`, `ack_received`, `bit_error` |
| Railway crossing controller | `models/railway.json` | `models/railway.smv` | `train_in_crossing`, `gate_is_down`, `unsafe_state` |
| Three-floor elevator controller | `models/elevator.json` | `models/elevator.smv` | `moving`, `doors_open`, `stalled` |

`gen_json.py` builds the JSON files by exploring each system's transition function from its initial state. The `.smv` files are written separately and do not depend on it.

    python3 gen_json.py models

## Model sizes

| System | States | Transitions |
|--------|--------|-------------|
| philosophers | 14 | 28 |
| peterson | 20 | 34 |
| abp | 22 | 32 |
| railway | 17 | 47 |
| elevator | 33 | 45 |

## Validation with NuSMV

    NuSMV -r models/philosophers.smv

The reachable-state count printed by NuSMV matches the number of states in the corresponding JSON model for all five systems.

## Modeling notes

- **Philosophers:** each philosopher is thinking, holding the left fork or eating. Fork availability is derived from these local states. The state in which all three hold their left fork is the deadlock and has a self-loop.
- **Peterson:** interleaving semantics with a program counter per process. A blocked busy-wait iteration does not change the state, so it is not a transition.
- **ABP:** lost, corrupted and unacknowledged cases return to the send state (timeout and retransmission). A duplicate packet is discarded and re-acknowledged, so it is never accepted twice. `packet_lost` labels only the loss of a data packet.
- **Railway:** synchronous product of train, gate and controller; each component either makes one permitted local transition or stays. The unsafe fast-train scenario is reachable.
- **Elevator:** positions between floors are explicit states. The cabin stops at every floor it reaches, requests are accepted only while idle, and an emergency stop leads to a terminal stalled state with a self-loop.
