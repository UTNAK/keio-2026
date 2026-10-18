<table width="100%">
  <tr>
    <td align="left" valign="middle">
      <strong>Agentic Product Concept Modeling 2026</strong><br>
      Laurent Balmelli, Hidekazu Nishimura<br>
      vers 2, 18/10/26
    </td>
    <td align="right" valign="middle">
      <img src="./keio-logo.png" alt="Keio University" width="140">
    </td>
  </tr>
</table>

---

# Load and Display the Official Vehicle Model

In this guide, you will load an official SysML v2 example and display part of its vehicle configuration in Jupyter. It is a friendly next step after [Creating and Displaying Your First SysML v2 Model](./first_model.md).

The three names below describe different parts of the workflow:

- **SysML v2** is the modeling language used to describe systems.
- **SimpleVehicleModel** is an official SysML v2 model and package from the SysML v2 Release repository.
- **OpenSysML** is the Jupyter kernel and rendering tool used to execute SysML cells and display views.

## 1. Download the official example

Open a terminal and run these commands from the main project directory:

```bash
cd ~/keio_2026
git clone --depth 1 \
  https://github.com/Systems-Modeling/SysML-v2-Release.git \
  workspace/samples/SysML-v2-Release
```

The host directory `workspace/samples` is mounted read-only inside the Jupyter container at `/home/keio/work/samples`. The full host `workspace/` directory is mounted at `/home/keio/work`, which is the Jupyter file-browser root. Copy any reference model you want to modify into `workspace/models/`; do not edit the reference checkout.

## 2. Load the official model

Open JupyterLab, create a notebook with the **SysML v2 (OpenSysML)** kernel, and run this command in a code cell:

```text
%load "/home/keio/work/samples/SysML-v2-Release/sysml/src/examples/Vehicle Example/SysML v2 Spec Annex A SimpleVehicleModel.sysml"
```

The expected result includes:

```text
✓ package SimpleVehicleModel
```

The loaded package contains the official vehicle definitions and configurations that you will use in the view below.

## 2.1 Copy a model into your editable model folder

The official checkout is read-only. If you want to experiment with the source model, copy the individual model file from the host terminal into `workspace/models/`:

```bash
cp "workspace/samples/SysML-v2-Release/sysml/src/examples/Vehicle Example/SysML v2 Spec Annex A SimpleVehicleModel.sysml" \
  workspace/models/vehicle-example.sysml
```

The copy appears in Jupyter as `/home/keio/work/models/vehicle-example.sysml`. Load that copy when you want to work from your own model:

```text
%load /home/keio/work/models/vehicle-example.sysml
```

## 3. Define a vehicle view

In a new SysML code cell, enter:

```sysml
package OfficialVehicleViews {
    private import Views::*

    view vehicleConfigurationA {
        expose SimpleVehicleModel::VehicleConfigurations::
            VehicleConfiguration_a::PartsTree::vehicle_a;
        expose SimpleVehicleModel::VehicleConfigurations::
            VehicleConfiguration_a::PartsTree::vehicle_a::**;
    }
}
```

Run the cell before rendering the view.

### What the view means

- `package OfficialVehicleViews` groups the presentation definition separately from the official model.
- `private import Views::*` makes the standard SysML view concepts available in this package.
- `view vehicleConfigurationA` declares a view named `vehicleConfigurationA`.
- The first `expose` selects the configured part `vehicle_a` as the starting point.
- The second `expose` uses `::**` to include the elements contained below `vehicle_a`, so the complete configuration tree can be displayed.
- The `::` separators identify elements through their qualified names, such as the `vehicle_a` part inside `VehicleConfiguration_a`.

## 4. Render the view

Run this command in another code cell:

```text
%render OfficialVehicleViews::vehicleConfigurationA mermaid
```

OpenSysML uses the general format:

```text
%render <package-name>::<view-name> <renderer>
```

Here, `OfficialVehicleViews::vehicleConfigurationA` is the qualified name of the view, and `mermaid` asks Jupyter to display it as a Mermaid diagram. The target after `%render` must be a declared `view`, not just a model package.

If the view does not render, restart the kernel and run the load, view, and render cells again in that order.
