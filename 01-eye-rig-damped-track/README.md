# Cartoon Eye Rig in Blender — Squash & Stretch Without a Lattice

Project files for [this video](https://youtube.com/watch?v=XXXX).

A stretchy cartoon eye rig built entirely from bones, so it exports
straight to GLB or FBX. No lattice, no mesh deformers, no shape keys.

**The concept:** a rocker bone sets *which direction* the eye squashes,
a stretch bone does the squashing, and a counter-rotation bone cancels
the rotation so the eye deforms without tumbling. The eyeball still
rotates inside the squashed shape instead of popping through the lids.

**Gotchas covered:**

- Copy Rotation in Local space copies numbers, not directions — so it
  only cancels correctly on bones that share an orientation.
- Damped Track breaks squash and stretch. It runs after the squash, so
  it drags the squash direction around. Fix is to aim on a separate
  bone outside the stretch.
- Flattening the deform hierarchy silently kills the effect on export.
  Looks fine in Blender, wrong in the engine.

Sliding a stretch handle sideways tilts the eye. That is intended.

## Files

- `cartoon-eye-rig.blend` — finished rig
- `eye_rig_ui.py` — the N-panel UI (also embedded in the .blend)

## Using the rig

Select the armature, then open the N-panel and go to the **Item** tab.
Toggles for each control group, plus an Eye Follow slider.

Blender blocks embedded scripts by default. If the panel is missing,
click **Allow Execution** on the banner when the file opens.

## Blender version

5.2
