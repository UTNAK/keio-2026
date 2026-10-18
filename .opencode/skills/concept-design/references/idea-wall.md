# Idea Wall example

This small example uses the course's established SysML v2 package, `part def`, part usage, and view syntax. It shows a logical structure only; it does not yet express scenario behavior, criteria traceability, or realization choices. Run it in the pinned OpenSysML kernel before calling it valid.

```sysml
package IdeaWall {
    part def Idea;
    part def Capture;
    part def Storage;
    part def Display;
    part def Analytics;

    part ideaWall {
        part capture : Capture;
        part storage : Storage;
        part display : Display;
        part analytics : Analytics;
    }
}

package IdeaWallViews {
    private import Views::*;

    view completeConcept {
        expose IdeaWall;
        expose IdeaWall::**;
    }
}
```

For a disposable kernel check, enter the model and view declarations in cells, then run `%render IdeaWallViews::completeConcept mermaid`. A `part def Capture;` defines a reusable type; `part capture : Capture;` is a usage in the `ideaWall` configuration.

Possible assumptions: participants contribute from different locations; related ideas can be found. Ask the student what observable criterion tests each assumption and which responsibility addresses it. Keep concrete parts and services in a separate Day 4 realization note.
