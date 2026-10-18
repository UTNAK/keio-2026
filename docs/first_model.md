<table width="100%">
  <tr>
    <td align="left" valign="middle">
      <strong>Agentic Product Concept Modeling 2026</strong><br>
      Laurent Balmelli, Hidekazu Nishimura<br>
      vers 3, 18/10/26
    </td>
    <td align="right" valign="middle">
      <img src="./keio-logo.png" alt="Keio University" width="140">
    </td>
  </tr>
</table>

---

# Creating and Displaying Your First SysML v2 Model

This guide explains how to create a simple SysML v2 model in Jupyter, define what should appear in a diagram, and render that diagram.

## 1. Open a SysML notebook

1. Open JupyterLab in your browser, http://localhost:8888/lab and use opensysml as token.
2. In the file browser, open the `notebooks/` folder and create a new notebook there. This saves it under the persistent host folder `workspace/notebooks/`.
3. Select **SysML v2 (OpenSysML)** as the notebook kernel.
4. Enter the cells below in order and run each one with **Shift+Enter**.

The SysML kernel keeps the declarations from executed cells in memory. The model cell must therefore be executed before the view cell, and the view cell before the render command. Restarting the kernel clears this in-memory model.

The course workspace makes the OpenSysML examples available at `/home/keio/work/samples`. The host `workspace/samples` directory is mounted read-only. The whole host `workspace/` directory is mounted at `/home/keio/work`, so notebooks, models, chats, and course files persist together across container rebuilds.

## 2. Load the OpenSysML views example

The recommended first exercise is the checked-out OpenSysML views demo. In a new SysML code cell, run:

```text
%load /home/keio/work/samples/OpenSysML/examples/views-demo.sysml
```

The file declares the `LanderViews` views. Render them in separate cells:

```text
%render LanderViews::interfaces mermaid
%render LanderViews::descentStates mermaid
%render LanderViews::descentFlow mermaid
%render LanderViews::partsTable markdown
```

`%render` targets a declared view and chooses its output format. Mermaid output is displayed as a diagram in Jupyter; the parts table is returned as Markdown.

## 3. Create the model

Enter the following in the first code cell:

```sysml
package KeioVehicle {
    part def Wheel;

    part def Vehicle {
        part wheels[4] : Wheel;
    }

    part car : Vehicle;
}
```

Run the cell. A successful result includes:

```text
✓ package KeioVehicle
```

### What the model means

- `package KeioVehicle { ... }` creates a named container for related model elements. A package organizes the model and provides a namespace; it is not itself a diagram.
- `part def Wheel;` defines a reusable type of part called `Wheel`.
- `part def Vehicle { ... }` defines a reusable `Vehicle` type.
- `part wheels[4] : Wheel;` says that a `Vehicle` contains four parts named `wheels`, each typed by `Wheel`.
- `part car : Vehicle;` creates a part named `car` using the `Vehicle` definition.
- `::` identifies an element through its qualified path. For example, `KeioVehicle::car` means the element `car` inside the `KeioVehicle` package.

## 4. Define a view

The package contains the model, but Jupyter still needs instructions describing which elements should appear in a diagram. A SysML `view` provides those instructions.

Enter the following in a new code cell:

```sysml
package KeioViews {
    private import Views::*;

    view completeVehicleModel {
        expose KeioVehicle;
        expose KeioVehicle::**;
    }
}
```

Run the cell.

### What the view means

- `package KeioViews` keeps presentation definitions separate from the system model.
- `private import Views::*;` makes the standard SysML view concepts available inside this package.
- `view completeVehicleModel` defines a view named `completeVehicleModel`.
- `expose KeioVehicle;` includes the model package itself.
- `expose KeioVehicle::**;` recursively includes the elements contained in that package.

A **package** organizes and contains model information. A **view** selects model information for a particular presentation. The same package can therefore support several views—for example, a complete-model view, a subsystem view, or a view showing only selected elements.

## 5. Render the view

Enter this command in another code cell:

```text
%render KeioViews::completeVehicleModel mermaid
```

Run the cell. Jupyter should display the model as a diagram.

`%render` is an OpenSysML Jupyter command, not a SysML language declaration. Its basic format is:

```text
%render <qualified-view-name> <output-format>
```

In this example:

- `KeioViews::completeVehicleModel` is the qualified name of the view.
- `mermaid` requests a Mermaid diagram that Jupyter can display directly.

The target of `%render` must be a **view**. For example, `%render KeioVehicle` fails because `KeioVehicle` is a package, not a view.

## 6. Create another model

Use the same three-step pattern for every exercise:

1. Define the model in a package.
2. Define a view that exposes the required model elements.
3. Render the qualified name of that view.

When creating another model, change the names consistently:

```sysml
package MySystem {
    // Definitions and parts
}

package MySystemViews {
    private import Views::*;

    view completeModel {
        expose MySystem;
        expose MySystem::**;
    }
}
```

Render it with:

```text
%render MySystemViews::completeModel mermaid
```

## Troubleshooting

- **`not a view`**: check that the name after `%render` identifies a `view`, not a package or part.
- **Name not found**: execute the model and view cells before the render cell.
- **Unexpected old definitions**: restart the kernel and run all cells again from the top.

## Ask OpenCode about the live notebook

Jupyter AI can connect OpenCode to the active notebook through Jupyter MCP tools. The agent can read unsaved cells and, when asked, add cells or run them in the notebook's existing OpenSysML kernel. See [Using OpenCode in JupyterLab](opencode.md) for setup and a course-model walkthrough. Step 1 does not require separate approval before each notebook-cell edit or execution.
