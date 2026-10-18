# Idea Wall tutoring demonstration

Use the same student question in both passes:

> I want an Idea Wall where people can post ideas and find related ones. Should I make the model use a Raspberry Pi?

## General agent pass

The general course assistant should first clarify the user's scenario, then explain that a Raspberry Pi is a possible implementation choice. It should ask whether the product concept requires that technology or whether the student is already selecting a realization. It should not rewrite the model without a request.

## After loading `concept-design`

The SysML Design Coach should explicitly follow the Build Concept workflow: elicit the user/problem/value; identify abstract `Capture`, `Storage`, `Display`, and `Analytics` responsibilities; state an assumption about sharing ideas from different locations and a criterion for discovering related ideas; and keep Raspberry Pi in a separate Day 4 candidate note. It should ask the student which element or interaction addresses the criterion and why a reusable `part def` differs from a usage in this wall. The skill adds the sequence and outputs; the coach supplies tutoring behavior.

## Example course model

`idea-wall.sysml` gives a small technology-independent structure and view. Validate it in the pinned OpenSysML kernel with `%load /opt/course/opencode/examples/idea-wall.sysml`, then `%render IdeaWallViews::completeConcept mermaid`. Kernel success validates compatibility with this course distribution, not all SysML v2 implementations. The example intentionally does not claim complete behavior or criteria traceability; the student should extend it from their own scenario.
