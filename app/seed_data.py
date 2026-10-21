"""Seed content for the demo workshop.

All dates are computed relative to today at seed time so the calendar, the
overview's "today's fittings" list and the recent builds always look alive.
"""

from __future__ import annotations

STAFF = [
    {
        "name": "Cenius Ashby",
        "email": "cenius@cenius.ai",
        "password": "cenius",
        "role": "admin",
    },
    {
        "name": "Marta Whitlock",
        "email": "marta@wheelwrightworkshop.co.uk",
        "password": "cenius",
        "role": "staff",
    },
    {
        "name": "Dorian Pengelly",
        "email": "dorian@wheelwrightworkshop.co.uk",
        "password": "cenius",
        "role": "staff",
    },
]

CLIENTS = [
    {
        "name": "Bodmin Heritage Trust",
        "contact_email": "enquiries@bodminheritage.org.uk",
        "phone": "01208 821 440",
        "heritage_notes": (
            "Restoring four narrow-wheel timber wagons for the museum yard. Felloes in "
            "seasoned oak, finished to the 1890s profile; spokes to match the surviving "
            "front axle on wagon No.1."
        ),
    },
    {
        "name": "Trewithen Estate",
        "contact_email": "office@trewithenestate.co.uk",
        "phone": "01726 882 210",
        "heritage_notes": (
            "Estate lorry and hay wagon kept in working order for the summer open days. "
            "Original iron tyres are to be re-used where the metal is sound."
        ),
    },
    {
        "name": "Reverend Alistair Pike",
        "contact_email": "alistair.pike@kernowparish.org.uk",
        "phone": "01726 640 118",
        "heritage_notes": (
            "Parish boundary procession cart, carried by hand on Rogation Sunday. Light "
            "ash felloes, and the tyre banded rather than shrunk so it stays cool in use."
        ),
    },
    {
        "name": "Lostwithiel Museum",
        "contact_email": "curator@lostwithielmuseum.org.uk",
        "phone": "01208 872 207",
        "heritage_notes": (
            "Display wheel for the lead-mining gallery, mounted behind glass. Static duty "
            "only, so the commission favours a faithful surface finish over load capacity."
        ),
    },
    {
        "name": "Padstow Harbour Board",
        "contact_email": "harbour@padstowboard.co.uk",
        "phone": "01841 532 340",
        "heritage_notes": (
            "Pair of hand-barrow wheels for the net loft demonstration days. Kept "
            "outdoors, so both the felloe stock and the tyre band want a heavy tar finish."
        ),
    },
    {
        "name": "Fiona Kernow",
        "contact_email": "fiona.kernow@trembroath.co.uk",
        "phone": "07791 402 118",
        "heritage_notes": (
            "Private commission: a 48 inch farm tip cart to match the one her grandfather "
            "built at Trembroath. Wants the tool marks left visible under the linseed."
        ),
    },
    {
        "name": "Gwennap Parish Council",
        "contact_email": "clerk@gwennapparish.co.uk",
        "phone": "01209 891 233",
        "heritage_notes": (
            "Mining heritage trail marker wheel on a low post at the Balduff gate. "
            "Decorative only; needs to survive salt wind and a decade of grazing cattle."
        ),
    },
    {
        "name": "Rosemundy Farm",
        "contact_email": "bill.ressor@rosemundyfarm.co.uk",
        "phone": "01872 553 901",
        "heritage_notes": (
            "Cider press wheel still turned by hand each autumn. Wants the hub re-bushed "
            "and the tyre banded at the same time as the new spokes go in."
        ),
    },
    {
        "name": "St Endellion Festival Trust",
        "contact_email": "hannah@stendellionfestival.org.uk",
        "phone": "01208 880 918",
        "heritage_notes": (
            "Props cart for the summer concert season. Built light so two stagehands can "
            "lift it; decorative iron tyre only on the outer face."
        ),
    },
    {
        "name": "Calum Trewin",
        "contact_email": "calum.trewin@penpoll.co.uk",
        "phone": "07700 900 412",
        "heritage_notes": (
            "Rebuild of a gun carriage wheel recovered from a barn floor at Penpoll. "
            "Felloes to be scarfed rather than bent, as the originals show scarf joints."
        ),
    },
]

# (reference, client name, felloes, spokes, diameter, status, days_ago, notes)
BUILDS = [
    (
        "CW-1041",
        "Bodmin Heritage Trust",
        14,
        14,
        54.0,
        "awaiting_tyre",
        6,
        "Front wheel for wagon No.1. Oak felloes jointed and ready for the iron tyre.",
    ),
    (
        "CW-1042",
        "Bodmin Heritage Trust",
        14,
        14,
        54.0,
        "in_build",
        3,
        "Rear wheel for wagon No.1, built to the front wheel's profile.",
    ),
    (
        "CW-1043",
        "Trewithen Estate",
        12,
        12,
        48.0,
        "complete",
        34,
        "Estate lorry wheel. Original tyre re-used with a new band shrunk on.",
    ),
    (
        "CW-1044",
        "St Endellion Festival Trust",
        12,
        12,
        46.5,
        "in_build",
        9,
        "Light props cart wheel; spokes turned down thinner than the pattern calls for.",
    ),
    (
        "CW-1045",
        "Lostwithiel Museum",
        10,
        10,
        42.0,
        "awaiting_tyre",
        12,
        "Display wheel. Surface finish matters more than the spoke count here.",
    ),
    (
        "CW-1046",
        "Padstow Harbour Board",
        8,
        10,
        36.0,
        "in_build",
        2,
        "First of a pair of hand-barrow wheels for the net loft.",
    ),
    (
        "CW-1047",
        "Fiona Kernow",
        14,
        14,
        48.0,
        "awaiting_tyre",
        15,
        "Farm tip cart wheel. Tool marks to be left visible under the linseed.",
    ),
    (
        "CW-1048",
        "Gwennap Parish Council",
        12,
        12,
        44.0,
        "complete",
        41,
        "Trail marker wheel, tarred and banded against the salt wind.",
    ),
    (
        "CW-1049",
        "Rosemundy Farm",
        10,
        12,
        40.0,
        "in_build",
        5,
        "Cider press wheel; hub re-bushed while the new spokes are fitted.",
    ),
    (
        "CW-1050",
        "Reverend Alistair Pike",
        12,
        12,
        47.0,
        "in_build",
        4,
        "Procession cart wheel, banded tyre so it stays cool on the road.",
    ),
    (
        "CW-1051",
        "Calum Trewin",
        14,
        16,
        50.0,
        "awaiting_tyre",
        8,
        "Gun carriage wheel rebuilt from the Penpoll find. Scarfed felloes.",
    ),
    (
        "CW-1052",
        "Trewithen Estate",
        14,
        14,
        52.0,
        "complete",
        52,
        "Spare hay wagon wheel, finished for the estate store.",
    ),
]

# (wheel reference, day offset from today, slot, status, notes)
FITTINGS = [
    ("CW-1041", 0, "09:00", "scheduled", "Iron tyre shrunk on this morning; bring the wagon hub."),
    ("CW-1045", 0, "11:00", "scheduled", "Display wheel, banded tyre, no load test needed."),
    ("CW-1051", 0, "14:00", "scheduled", "Scarfed felloe wheel; check the band fit twice."),
    ("CW-1043", 0, "16:00", "completed", "Estate lorry wheel finished and collected."),
    ("CW-1048", -1, "10:00", "completed", "Marker wheel banded and tarred."),
    ("CW-1042", -1, "13:00", "cancelled", "Client asked to move the wagon slat work first."),
    ("CW-1047", 1, "09:00", "scheduled", "Tip cart wheel; client will watch the banding."),
    ("CW-1044", 2, "10:00", "scheduled", "Light props cart wheel, thin band."),
    ("CW-1049", 3, "08:00", "scheduled", "Cider press wheel alongside the hub re-bush."),
    ("CW-1050", 5, "15:00", "scheduled", "Procession cart wheel, cool band."),
    ("CW-1046", 8, "11:00", "scheduled", "First hand-barrow wheel of the pair."),
    ("CW-1042", 12, "09:00", "scheduled", "Rear wagon wheel, re-booked after the slat work."),
    ("CW-1041", -26, "09:00", "completed", "Earlier front wheel trial fit."),
    ("CW-1041", 19, "14:00", "scheduled", "Front wheel final fit before the museum delivery."),
]
