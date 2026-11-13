\
\
\
\
\
\
\
\

import json
import os
import sys
from collections import OrderedDict

OUT = sys.argv[1] if len(sys.argv) > 1 else "models"
os.makedirs(OUT, exist_ok=True)

def uniq(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def build(name, props, init, succ, label, namer):

    order, seen, queue = [], {init}, [init]
    graph = {}
    while queue:
        s = queue.pop(0)
        order.append(s)
        nxt = uniq(succ(s))
        graph[s] = nxt
        for t in nxt:
            if t not in seen:
                seen.add(t)
                queue.append(t)
    states = OrderedDict()
    for s in order:
        labs = label(s)
        assert all(l in props for l in labs), (name, s, labs)
        assert graph[s], (name, s, "dead end")
        states[namer(s)] = OrderedDict(
            [("labels", labs), ("transitions", [namer(t) for t in graph[s]])]
        )
    doc = OrderedDict(
        [
            ("atomic_propositions", props),
            ("initial_states", [namer(init)]),
            ("states", states),
        ]
    )
    with open(os.path.join(OUT, name + ".json"), "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    n_tr = sum(len(v) for v in graph.values())
    print(f"{name:12s} states={len(order):4d} transitions={n_tr:4d}")

def phil_succ(s):
    out = []
    for i in range(3):
        prev, nxt = (i - 1) % 3, (i + 1) % 3
        me = s[i]

        def setme(v):
            t = list(s)
            t[i] = v
            return tuple(t)

        if me == "T" and s[prev] != "E":
            out.append(setme("H"))
        elif me == "H" and s[nxt] == "T":
            out.append(setme("E"))
        elif me == "E":
            out.append(setme("T"))
    if not out:
        out.append(s)
    return out

def phil_label(s):
    labs = [f"P{i}_eating" for i in range(3) if s[i] == "E"]
    if s == ("H", "H", "H"):
        labs.append("deadlock")
    return labs

build(
    "philosophers",
    ["P0_eating", "P1_eating", "P2_eating", "deadlock"],
    ("T", "T", "T"),
    phil_succ,
    phil_label,
    lambda s: "".join(s),
)

def pet_succ(s):
    pc, fl, turn = [s[0], s[1]], [s[2], s[3]], s[4]
    out = []
    for i in (0, 1):
        j = 1 - i
        npc, nfl, nturn = list(pc), list(fl), turn
        if pc[i] == "idle":
            nfl[i] = 1
            npc[i] = "set_turn"
        elif pc[i] == "set_turn":
            nturn = j
            npc[i] = "waiting"
        elif pc[i] == "waiting":
            if fl[j] == 1 and turn == j:
                continue
            npc[i] = "cs"
        elif pc[i] == "cs":
            nfl[i] = 0
            npc[i] = "idle"
        out.append((npc[0], npc[1], nfl[0], nfl[1], nturn))
    return out

def pet_label(s):
    labs = []
    if s[0] == "cs":
        labs.append("P0_in_CS")
    if s[1] == "cs":
        labs.append("P1_in_CS")
    if s[2]:
        labs.append("flag0")
    if s[3]:
        labs.append("flag1")
    if s[4] == 1:
        labs.append("turn_is_1")
    return labs

build(
    "peterson",
    ["P0_in_CS", "P1_in_CS", "flag0", "flag1", "turn_is_1"],
    ("idle", "idle", 0, 0, 0),
    pet_succ,
    pet_label,
    lambda s: f"{s[0]}.{s[1]}.f{s[2]}{s[3]}.t{s[4]}",
)

def abp_succ(s):
    ph, sb, rb = s
    if ph == "send":
        return [("data_tx", sb, rb)]
    if ph == "data_tx":
        rb2 = 1 - rb if sb == rb else rb
        return [("data_lost", sb, rb), ("data_corrupt", sb, rb), ("ack_tx", sb, rb2)]
    if ph in ("data_lost", "data_corrupt", "ack_lost"):
        return [("send", sb, rb)]
    if ph == "ack_tx":
        return [("ack_lost", sb, rb), ("ack_ok", sb, rb)]
    if ph == "ack_ok":
        return [("send", 1 - sb, rb)]
    raise ValueError(ph)

def abp_label(s):
    return {"data_lost": ["packet_lost"], "data_corrupt": ["bit_error"], "ack_ok": ["ack_received"]}.get(s[0], [])

build(
    "abp",
    ["packet_lost", "ack_received", "bit_error"],
    ("send", 0, 0),
    abp_succ,
    abp_label,
    lambda s: f"{s[0]}_s{s[1]}_r{s[2]}",
)

def rw_succ(s):
    train, gate, ctrl = s
    t_opts = {
        "far": ["far", "approaching"],
        "approaching": ["approaching", "in_crossing"],
        "in_crossing": ["in_crossing", "passed"],
        "passed": ["passed"],
    }[train]

    if ctrl == "idle" and train == "approaching":
        c_opts = ["idle", "closing_req"]
    elif ctrl == "closing_req" and train == "passed":
        c_opts = ["closing_req", "opening_req"]
    elif ctrl == "opening_req" and gate == "open":
        c_opts = ["opening_req", "idle"]
    else:
        c_opts = [ctrl]

    if gate == "open" and ctrl == "closing_req":
        g_opts = ["open", "lowering"]
    elif gate == "lowering" and ctrl == "closing_req":
        g_opts = ["lowering", "closed"]
    elif gate == "lowering" and ctrl == "opening_req":
        g_opts = ["lowering", "raising"]
    elif gate == "closed" and ctrl == "opening_req":
        g_opts = ["closed", "raising"]
    elif gate == "raising":
        g_opts = ["raising", "open"]
    else:
        g_opts = [gate]

    return [(t, g, c) for t in t_opts for g in g_opts for c in c_opts]

def rw_label(s):
    labs = []
    if s[0] == "in_crossing":
        labs.append("train_in_crossing")
    if s[1] == "closed":
        labs.append("gate_is_down")
    if s[0] == "in_crossing" and s[1] != "closed":
        labs.append("unsafe_state")
    return labs

build(
    "railway",
    ["train_in_crossing", "gate_is_down", "unsafe_state"],
    ("far", "open", "idle"),
    rw_succ,
    rw_label,
    lambda s: f"{s[0]}.{s[1]}.{s[2]}",
)

def el_succ(s):
    pos, d, door, req, st = s
    if st:
        return [s]
    out = []
    at_floor_idle = d == "stat" and door == "closed" and pos % 2 == 0
    if at_floor_idle:
        if req is None:
            out += [(pos, d, door, r, False) for r in (0, 2, 4)]
        elif req == pos:
            out.append((pos, "stat", "opening", req, False))
        elif req > pos:
            out.append((pos + 1, "up", "closed", req, False))
        else:
            out.append((pos - 1, "down", "closed", req, False))
    elif d != "stat":
        out.append(((pos + 1) if d == "up" else (pos - 1), "stat", "closed", req, False))
        out.append((pos, "stat", "closed", req, True))
    elif door == "opening":
        out.append((pos, "stat", "open", None, False))
    elif door == "open":
        out.append((pos, "stat", "closing", req, False))
    elif door == "closing":
        out.append((pos, "stat", "closed", req, False))
    return out

def el_label(s):
    labs = []
    if s[1] != "stat":
        labs.append("moving")
    if s[2] == "open":
        labs.append("doors_open")
    if s[4]:
        labs.append("stalled")
    return labs

POSN = ["F1", "B12", "F2", "B23", "F3"]
REQN = {None: "noreq", 0: "req1", 2: "req2", 4: "req3"}
build(
    "elevator",
    ["moving", "doors_open", "stalled"],
    (0, "stat", "closed", None, False),
    el_succ,
    el_label,
    lambda s: f"{POSN[s[0]]}.{s[1]}.{s[2]}.{REQN[s[3]]}" + (".STALLED" if s[4] else ""),
)
