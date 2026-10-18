<table width="100%">
  <tr>
    <td align="left" valign="middle">
      <strong>Agentic Product Concept Modeling 2026</strong><br>
      Laurent Balmelli, Hidekazu Nishimura<br>
      vers 1, 13/10/26
    </td>
    <td align="right" valign="middle">
      <img src="./keio-logo.png" alt="Keio University" width="140">
    </td>
  </tr>
</table>

---

# Visual Concept Making Workflows

This guide separates the Day 3 product concept from Day 4 proof-of-concept realizations. The SysML Design Coach provides tutoring; the three course skills provide the step-by-step workflows. The student remains responsible for design decisions and can ask for a hint, a direct explanation, or an alternative at any time.

## Day 3: Build Concept

Start with the problem, intended user, scenario, and product value. State assumptions and observable feasibility criteria. Model logical responsibilities, reusable types and usages, relationships, interfaces, and essential behaviors in SysML v2. Link important elements to criteria and define the minimum capability a future realization must satisfy. Validate with the pinned OpenSysML kernel and render views where useful.

Keep the canonical concept technology-independent. If a student proposes a Raspberry Pi, a specific display, cloud database, or AI service, ask whether it is required by the problem or is a candidate implementation. Preserve it in a separate Day 4 note unless a justified product requirement mandates it. Before moving to Day 4, ask the student to explain a pivotal modeling choice.

## Day 4: Implement PoC

Load `poc-realization` with `/explore-poc`. Map the versioned concept and criteria to hardware, software, service, and assembly candidates. Search only through approved tools. For each sourced candidate, record its identity, supplier/project, model/version, relevant specification, direct URL, and retrieval date. Label marketing claims and inferences separately. Compare alternatives and interfaces, identify risks and gaps, and keep each realization model separate from the abstract concept. If web search is unavailable, request student-provided candidates and label them unverified.

## Day 4: Assess Feasibility and Refine

Load `feasibility-assessment` with `/assess-feasibility`. Compare each concept criterion against each realization using status `satisfied`, `partially satisfied`, `unsatisfied`, or `unverified`. Record evidence quality independently as `tested`, `specification-supported`, `inferred`, or `unsupported`. Link claims to tests, model checks, or sources. Identify integration uncertainty and practical innovation opportunities, then choose the smallest useful next experiment. A datasheet is not evidence that an integrated PoC works.

## Idea Wall example

The example starts with technology-independent responsibilities: `Capture`, `Storage`, `Display`, and `Analytics`. A participant contributes an idea; the concept retains it, presents selected ideas, and supports finding related ideas. Possible assumptions include that participants can contribute from different locations and that useful relationships can be found. Ask what observation would test each assumption. The runnable model is [`../opencode/examples/idea-wall.sysml`](../opencode/examples/idea-wall.sysml); a scripted comparison of the general assistant and the loaded concept-design workflow is in [`../opencode/examples/idea-wall-comparison.md`](../opencode/examples/idea-wall-comparison.md).

In the model, `part def Capture;` defines a reusable kind, while `part capture : Capture;` is a usage in the `ideaWall` product configuration. The example only demonstrates course-kernel syntax and a logical structure; students should add behavior, requirements, criteria links, and alternatives for their own scenario.

## Entry points

In JupyterLab Chat, select **SysML Design Coach**. Use `/start-concept-design`, `/explore-poc`, or `/assess-feasibility` to activate the intended skill. The coach supplies the tutoring role; the selected skill supplies the methodology. The instructor-configurable question bank is [`../opencode/question-bank.json`](../opencode/question-bank.json).
