# Rebel Control Center UI Concept

## Overview
Design a "Rebel Control Center" interface that fuses Star Wars holographic aesthetics with macOS clarity and analog synth physicality. The experience should make automations feel like tangible modules inside a starship while keeping the system approachable for low-code and code-first users alike.

## Design Pillars
| Principle | Description | Why It Matters |
|-----------|-------------|----------------|
| Physicality | Present workflows and tools as modules the operator can grab, patch, and tune. | Tangible interactions improve comprehension of complex automations. |
| Clarity through Texture | Layer translucency, subtle gradients, and disciplined spacing. | macOS-inspired depth separates interface planes without clutter. |
| Ambient Immersion | Use Star-Wars-style glow, motion, and audio cues sparingly. | Establishes a diegetic command-deck feeling while staying functional. |
| Immediate Feedback | Every patch, knob, or toggle reacts with light and motion. | Reinforces confidence and supports rapid iteration. |
| Dual Nature | Seamlessly bridge visual patching with direct code editing. | Keeps low-code and code-first workflows synchronized. |

## Key Views
### 1. Command Deck (Dashboard)
- **Layout:** Widescreen cockpit panel with three columns.
  - Left: Temporal status and MCP server health cards.
  - Center: "Next Runs" holo-timeline with upcoming executions.
  - Right: Mini terminal for quick commands.
- **Style:** Dark metal surfaces, cyan/orange holographic accents, SF Pro typography.
- **Purpose:** Provide situational awareness so operators feel like pilots, not sysadmins.

### 2. Patch Bay (Visual Builder)
- **Metaphor:** Modular synth rack.
- **Elements:**
  - Workflow/tool modules with jack sockets for inputs/outputs.
  - Drag-and-drop virtual patch cables that auto-suggest compatible parameters.
  - Parameter knobs and switches for configuration and schedule toggles.
  - Double-click opens Monaco-based code editor overlay; hover shows quick docs.
- **Behavior:** Connections serialize to workflow config JSON; shift-drag creates conditional branches.

### 3. Workflow Inspector
- **Form:** macOS-style sidebar inspector with tabs (Overview, Activities, Code, Runs).
- **Details:**
  - Overview: metadata (name, schedule, namespace, timezone).
  - Activities: tools referenced and JSON Schemas.
  - Code: read-only view with optional edit toggle.
  - Runs: latest executions with status indicators.
- **Signal:** Holographic glow when a workflow is scheduled/"armed".

### 4. Agent Console
- **Purpose:** Conversational surface for the LLM agent.
- **Features:**
  - Chat window with holo message bubbles.
  - Side panel showing planning/generation/validation phases as progress bars.
  - "Holo diff" viewer for generated code (transparent side-by-side layers).
  - Linear controls: Generate → Validate → Repair → Commit.

### 5. MCP Dock
- **Structure:** Bottom-aligned dock reminiscent of macOS.
- **Function:** Each icon represents an MCP server; clicking reveals tools.
- **Interaction:** Drag tools into Patch Bay to instantiate modules.

### 6. Chrono-Scope (Run Monitor)
- **Visualization:** Oscilloscope waveform where pulses represent workflow runs.
- **Encoding:** Color conveys status (success/failure), amplitude shows duration.
- **Interaction:** Selecting a pulse opens run details in the Inspector.

### 7. Config & Secrets Panel
- **Layout:** Card-based system preferences view.
- **Controls:** Knobs and toggles for LLM limits, retry policies, and Temporal settings.
- **Security:** Secret fields covered by "holo glass" that flickers when focused.

## Visual Language
| Element | Influence | Implementation Notes |
|---------|-----------|-----------------------|
| Base UI | macOS | Glassmorphism panels, SF Pro font, rounded rectangles. |
| Lighting | Star Wars | Cyan/orange glow, gentle flicker shaders, low-frequency pulse. |
| Interaction | Analog Synth | Drag cables, rotary knobs, toggle switches with detents. |
| Code Editor | Console + Hologram | Monaco editor skinned with transparent overlays. |
| Animations | Starship Controls | Smooth easing, slight parallax, responsive lighting. |
| Audio | Synth Bleed | Optional subtle clicks and hum on connects/toggles. |

## Component Hierarchy (React Example)
```
<AppShell>
 ├─ CommandDeck
 │   ├─ SystemStatusCard
 │   ├─ NextRunsTimeline
 │   └─ QuickCommandTerminal
 │
 ├─ PatchBay
 │   ├─ ModuleNode
 │   ├─ CableConnection
 │   └─ ParameterKnob
 │
 ├─ Inspector
 │   ├─ Tabs (Overview, Activities, Code, Runs)
 │   └─ StatusIndicator
 │
 ├─ AgentConsole
 │   ├─ ChatWindow
 │   ├─ PhaseProgress
 │   └─ DiffViewer
 │
 ├─ MCPDock
 │   ├─ ServerIcon
 │   └─ ToolPopover
 │
 ├─ ChronoScope
 │   └─ RunPulse
 │
 └─ ConfigPanel
     ├─ ConfigCard
     └─ SecretField
```

## Interaction Highlights
- Drag a tool from MCP Dock to Patch Bay to create a new module node.
- Connect module outputs to inputs to define data flow; connections persist in workflow config.
- Double-click a module to open the code editor overlay; Cmd + E toggles visual/code modes.
- Cmd + Enter triggers "Run now" for the active workflow.
- Modules pulse with glow when executing; shift-drag cables create conditional branches.

## Technical Stack & Integration
- **Framework:** React + Tailwind CSS + Framer Motion for animation.
- **Editors & Viz:** Monaco editor for code, D3 (or React Three Fiber) for Chrono-Scope waveform.
- **State Hooks:** `useTemporalStatus`, `usePatchBayState`, etc., backed by FastAPI endpoints.
- **Persistence:** Patch layout stored as JSON; cables defined by `{from, to, param}` objects.
- **Theme Engine:** CSS variables supporting default dark theme with optional "Holo" toggle.
- **Audio:** Optional Web Audio API layer for subtle synth cues.

## MVP Milestones
1. PatchBay displays existing workflows and MCP tools as modules.
2. Visual connections persist and map to workflow configuration.
3. AgentConsole performs the plan → generate → validate → repair → commit flow.
4. CommandDeck surfaces system status, next runs, and recent runs.
5. MCPDock lists servers and supports drag-to-PatchBay.
6. Chrono-Scope renders last ten runs with selectable detail.

## Suggested Task Breakdown
- U-001: Implement hybrid Star Wars/macOS theme system.
- U-002: Build CommandDeck with real-time system telemetry.
- U-003: Develop PatchBay with nodes, cables, and persistence.
- U-004: Create Inspector with overview/activity/code/run tabs.
- U-005: Implement AgentConsole chat, progress indicators, and diff viewer.
- U-006: Build MCPDock with drag-to-module interactions.
- U-007: Implement Chrono-Scope waveform visualization.
- U-008: Build ConfigPanel cards for LLM, Git, Temporal, and secrets.
- U-009: Wire components to FastAPI services.
- U-010: Add ambient animation and audio polish.

## Next Steps
Consider extending this document with a color and motion palette to hand off to design/animation partners. Document shader parameters, animation timings, and audio cues to preserve the diegetic Starship experience.
