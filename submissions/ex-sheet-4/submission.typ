#import "../template/template.typ": *

#show: template.with(
  course: "Agent-based Control in Energy Systems", 
  authors: ("Tim Hesse", "Michael Krah").sorted(),
  group: 8,
  number: 4,
  tutor: "Rico Schrage",
  tutor-mail: "rico.schrage@uni-oldenburg.de",
  date: datetime(day: 26, month: 11, year: 2024)
)

== Exercise 1
Possible parameters that our `Observer` could monitor are:
 - number of color changes
 - system state, i.e., color of each Agent
 - color state history

== Exercise 2
One of the possible reaction could be to a repeated color state.
If a color has already been tried, the controller could intervene and change one of the 
agent's colors to switch to a color state which has not yet been tried.

Another reaction could be to an unnecessary color switch.
If the other two agents use the same color, there is no need to switch 
(but this could still happen at random).
The controller could intervene to prevent this switch (or change the agent's color to its 
original color).

== Exercise 3.2
We change the color state to a new "initial" color state.
The other discussed parameters are not implemented.

#pagebreak()

== Exercise 3.6

```
╭───┬────────────────────────────┬────────────────────────────╮
│ # │         Solution 1         │         Solution 2         │
├───┼────────────────────────────┼────────────────────────────┤
│ 0 │ ╭───────────────┬────────╮ │ ╭───────────────┬────────╮ │
│   │ │ no_messages   │ 6      │ │ │ no_messages   │ 12     │ │
│   │ │ solution_time │ 510900 │ │ │ solution_time │ 513900 │ │
│   │ ╰───────────────┴────────╯ │ ╰───────────────┴────────╯ │
│ 1 │ ╭───────────────┬────────╮ │ ╭───────────────┬────────╮ │
│   │ │ no_messages   │ 6      │ │ │ no_messages   │ 6      │ │
│   │ │ solution_time │ 479100 │ │ │ solution_time │ 317800 │ │
│   │ ╰───────────────┴────────╯ │ ╰───────────────┴────────╯ │
│ 2 │ ╭───────────────┬────────╮ │ ╭───────────────┬────────╮ │
│   │ │ no_messages   │ 6      │ │ │ no_messages   │ 12     │ │
│   │ │ solution_time │ 444800 │ │ │ solution_time │ 480400 │ │
│   │ ╰───────────────┴────────╯ │ ╰───────────────┴────────╯ │
│ 3 │ ╭───────────────┬────────╮ │ ╭───────────────┬────────╮ │
│   │ │ no_messages   │ 12     │ │ │ no_messages   │ 12     │ │
│   │ │ solution_time │ 670800 │ │ │ solution_time │ 510600 │ │
│   │ ╰───────────────┴────────╯ │ ╰───────────────┴────────╯ │
╰───┴────────────────────────────┴────────────────────────────╯
```

The time differences between the two solutions are often negligible.
Since we choose colors at random to find a valid solution, we sometimes require 6 or 12 
messages.
We always have modulo 6-based number of messages because every `ColorAgent` will send a 
color update to its two neighbors.

When one solution requires more messages than another it takes longer, albeit marginally.
