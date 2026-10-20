<table width="100%">
  <tr>
    <td align="left" valign="middle">
      <strong>Agentic Product Concept Modeling 2026</strong><br>
      Laurent Balmelli, Hidekazu Nishimura<br>
      vers 5, 20/10/26
    </td>
    <td align="right" valign="middle">
      <img src="./docs/keio-logo.png" alt="Keio University" width="140">
    </td>
  </tr>
</table>

---

# Course workspace and getting started

Use this repository to run the course notebooks, create SysML v2 models, and work with the SysML Design Coach. The course environment runs locally in Docker; your notebooks and models stay in your local workspace unless you choose to share them.

## Course materials

The entire `classes/` directory is included in this repository. Start with the [Day 1 class material](classes/day1/Agentic_Product_Concept_Modeling_2026-Day1.pdf); open it in your browser or download it for class.

## Current tooling

| Tool | Purpose |
| --- | --- |
| Docker Engine and Docker Compose | Build and start the course container. |
| JupyterLab | The browser interface for notebooks and the native Jupyter AI chat panel. |
| OpenSysML Jupyter kernel | Execute SysML v2 cells using `%load`, `%print`, and `%render`. |
| OpenCode through Jupyter AI | Chat with the SysML Design Coach using your selected provider and model. |
| Course status item | Show local recording and synchronization status when classroom collection is configured. |

The container installs pinned course versions of Jupyter AI, OpenSysML, and OpenCode. You do not need to install Python on your computer.

## Prerequisites

Before cloning the course repository, install Git and the open-source Docker Engine with the Docker Compose v2 plugin. Do not install Docker Desktop for this course. Docker Engine runs natively on Linux and inside a Linux environment on Windows or macOS.

### Windows: WSL2 and Docker Engine

1. Open PowerShell as Administrator and install Windows Subsystem for Linux (WSL2) with Ubuntu:

   ```powershell
   wsl --install
   ```

   Restart Windows if prompted, then open the installed Ubuntu terminal. See the [Microsoft WSL installation guide](https://learn.microsoft.com/en-us/windows/wsl/install) for older Windows versions or other Linux distributions.
2. Inside the Ubuntu terminal, install Git:

   ```bash
   sudo apt update
   sudo apt install -y git
   ```

3. Inside the same Ubuntu environment, install Docker Engine and the Compose plugin by following Docker’s [Ubuntu Engine installation guide](https://docs.docker.com/engine/install/ubuntu/). Select the packages for Docker Engine, including `docker-ce`, `docker-ce-cli`, `containerd.io`, `docker-buildx-plugin`, and `docker-compose-plugin`; do not install Docker Desktop.
4. Start the Docker service using the service method configured in your WSL distribution. On systemd-enabled WSL, use:

   ```bash
   sudo systemctl enable --now docker
   ```

Run the repository’s Git, Docker, and Compose commands from the Ubuntu terminal. Keeping the repository inside the WSL Linux filesystem, such as under `~/keio-2026`, gives Docker Linux-native file access.

### macOS: Colima and Docker Engine

Docker Engine is Linux-native, so on macOS run it in the open-source [Colima](https://colima.run/) Linux VM. Install Git with Apple’s Command Line Tools, then install Colima, the Docker CLI, and the Compose plugins with Homebrew:

```bash
xcode-select --install
brew install colima docker docker-compose docker-buildx
mkdir -p ~/.docker/cli-plugins
ln -sfn "$(brew --prefix)/opt/docker-compose/bin/docker-compose" ~/.docker/cli-plugins/docker-compose
ln -sfn "$(brew --prefix)/opt/docker-buildx/bin/docker-buildx" ~/.docker/cli-plugins/docker-buildx
colima start --runtime docker
```

If Homebrew is not installed, follow the [Homebrew installation instructions](https://brew.sh/) first. Colima supports both Intel Macs and Apple Silicon Macs; use its default architecture unless the project specifically requires amd64 emulation.

### Linux: Docker Engine

1. Install Git using your distribution’s package manager. For Debian or Ubuntu:

   ```bash
   sudo apt update
   sudo apt install -y git
   ```

   For Fedora, use `sudo dnf install git`.
2. Install Docker Engine and the Docker Compose v2 plugin using Docker’s [Linux Engine installation guide](https://docs.docker.com/engine/install/). Choose the page for your distribution and install Docker Engine, Docker CLI, Buildx, and the Compose plugin.
3. Start the Docker service if your distribution does not start it automatically. With systemd:

   ```bash
   sudo systemctl enable --now docker
   ```

Docker’s [post-installation guide](https://docs.docker.com/engine/install/linux-postinstall/) explains how to use Docker as a non-root user. Follow your distribution’s permission guidance before running the course commands without `sudo`.

For JupyterLab, use Google Chrome or another current Chromium-based browser, such as Chromium, Microsoft Edge, or Brave. The course instructions are written for this browser family.

Check that the commands are available:

```bash
git --version
docker --version
docker compose version
```

## Clone the course repository

The course repository is public. Clone it without GitHub credentials:

```bash
git clone https://github.com/lbalmelli/keio-2026.git
cd keio-2026
```

## Build and start JupyterLab

Build the container, then start the course environment:

```bash
make build
make up
```

Open [http://localhost:8888/lab](http://localhost:8888/lab) and sign in with the default Jupyter token `opensysml`. To use another token or port, set `JUPYTER_TOKEN` or `JUPYTER_PORT` in your terminal before `make up`.

JupyterLab is the only browser application. Open the native Jupyter AI chat panel and select the `sysml-design-coach` agent. Provider sign-in is separate from GitHub access and is needed for AI responses:

```bash
make opencode-auth
```

Follow your provider's sign-in prompts, then choose an authenticated provider and model in Jupyter AI. Never enter provider credentials in a notebook or chat.

## Load the sample model

Download the public OpenSysML course examples once:

```bash
make samples
```

Run this from the course repository directory. It creates `workspace/samples/OpenSysML` with a shallow checkout when it is absent. If a valid checkout is already present, the target leaves it unchanged; if the destination exists but is not a Git checkout, the command stops rather than overwriting it. The samples appear in JupyterLab at `/home/keio/work/samples` and are mounted read-only. Run `make samples` again after cloning if the sample folder is missing.

Open the notebook in JupyterLab and select the **SysML v2 (OpenSysML)** kernel. Follow [Creating and Displaying Your First SysML v2 Model](docs/first_model.md) to load and render the sample.

## Save your work

- New notebooks go in `workspace/notebooks/`.
- Save new SysML models in `workspace/models/` with distinct filenames.
- OpenCode provider configuration is stored in the persistent `opencode-state` Docker volume.
- Student-created chats, notebooks, models, and course evidence are local workspace data and are excluded from the public course repository by Git ignore rules. The starter notebook is distributed with the course. Do not force-add student work to Git.

The course status item may record visible course dialogue and scoped notebook/model activity locally in `workspace/private-course-data/`. In a fresh checkout, no instructor collector is configured, so there is no remote synchronization. If your instructor enables collection, enroll through the status item using the one-time code they provide. Read [Classroom Data and Privacy](docs/classroom-data-and-privacy.md) before using the environment for course evidence.

## Stop and restart

Stop the environment with `Ctrl+C` in the terminal running `make up`, or open another terminal in the repository and run:

```bash
make down
```

Start it again with `make up`. To rebuild after course updates, run `make build` first. Avoid `docker compose down --volumes` if you want to keep OpenCode provider sign-in.

## Start the course exercises

Read the exercises in this order:

1. [Creating and Displaying Your First SysML v2 Model](docs/first_model.md) — load the OpenSysML views example, create a small SysML v2 model, declare views, and render them.
2. [Load and Display the Official Vehicle Model](docs/official_vehicle_model.md) — load the official `SimpleVehicleModel`, define a view for a vehicle configuration, and render it.
3. [Using OpenCode in JupyterLab](docs/opencode.md) — ask OpenCode about the active notebook, add a cell, and execute a real course view with the existing SysML kernel.

The first guide uses the checkout created by `make samples`. The second guide explains how to clone the official SysML v2 Release repository into `workspace/samples/SysML-v2-Release` when you are ready for that exercise.

In both guides, commands beginning with `make`, `docker`, or `git` are run in the host terminal. Commands beginning with `%load` or `%render`, and SysML declarations, are entered in Jupyter code cells.

## Use the SysML Design Coach and skills

Open the native **Chat** panel in JupyterLab, select **SysML Design Coach**, and authenticate with `make opencode-auth` if you have not already. Choose an authenticated provider and model in Jupyter AI. Start the Day 3 concept workflow with `/start-concept-design`; use `/explore-poc` for Day 4 candidate realizations, `/component-to-sysml-v2` to model a selected component specification as a sourced `part def`, and `/assess-feasibility` to compare evidence. The component workflow reviews interface-relevant properties such as ports, connections, dimensions, and mass with you, then models the properties you select. These entry points load the matching course skill.

The coach provides the personalized tutoring role: it asks relevant open questions, offers graduated hints, and asks occasional comprehension questions. You make and explain the design decisions; the coach preserves your answers and does not assign automatic grades or mastery scores. The skills provide the step-by-step methodology. On Day 3, keep the concept technology-independent and describe **what** the product must do. On Day 4, model candidate **how** realizations separately and trace them back to the concept and its criteria. See [Visual Concept Making workflows](docs/visual-concept-making-workflows.md) for the full workflow.

The JupyterLab status item shows `Recording`, `Synced`, `Offline / queued`, or `Attention needed`. Click it to read the disclosure, enroll with a one-time code from the instructor, synchronize, or export local evidence. Course dialogue and scoped notebook/model activity are stored in the private, Git-ignored `workspace/private-course-data/` folder. A fresh checkout has no collector URL configured, so it records locally and does not submit data remotely. Offline evidence remains queued. Read [Classroom Data and Privacy](docs/classroom-data-and-privacy.md) before using the workspace for course evidence.

## Common problems

| Symptom | Solution |
| --- | --- |
| Docker daemon is unavailable | Start Docker Engine, WSL2, or Colima, then verify with `docker info`. |
| `docker compose` is unavailable | Install the Docker Compose v2 plugin and check `docker compose version`. |
| Port `8888` is already in use | Set `JUPYTER_PORT=8889`, run `make up`, and open `http://localhost:8889/lab`. |
| OpenCode is missing from the chat agent list | Run `make build`, then restart with `make down` and `make up`. |
| OpenCode has no response | Run `make opencode-auth` and select an authenticated provider and model in Jupyter AI. |
| OpenSysML kernel is missing | Run `make build`, then restart the container. Select **SysML v2 (OpenSysML)** from the notebook's Kernel menu. |
| Course sample cannot be found | Run `make samples`, then restart with `make down` and `make up`. |
| Jupyter rejects the token | Use `opensysml` unless you set `JUPYTER_TOKEN` before startup. |
| A saved model or notebook is missing after rebuild | Check `workspace/models/` and `workspace/notebooks/` on your computer; these folders persist outside the container. |

For notebook and tutor instructions, see the course guides above. For collection and privacy questions, contact your instructor.
