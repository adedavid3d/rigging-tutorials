# Exportable Cartoon Eye Rig — Full Breakdown

**Project:** Squash-and-stretch cartoon eye rig, Blender 5.2, no lattice, game-engine exportable
**Purpose:** YouTube tutorial reference + technical post-mortem
**Author:** Ade David (adedavid3d)

---

## 1. What this rig is trying to do

A normal eye rig points an eyeball at a target and calls it a day. A cartoon eye needs more than that:

1. The eye must **squash and stretch** — bulge forward, flatten, pop out.
2. The animator must be able to **choose which direction** the stretch happens in, on the fly.
3. When the eye is stretched, the eyeball must still **rotate inside** the deformed shape. It must not snap back to being a sphere and poke through the eyelids.
4. The eyelids must follow the deformation.
5. **No lattice, no shape keys driven by lattices, no mesh deformers.** Everything has to be bones, so it survives export to GLB/FBX for a game engine.

Point 5 is the constraint that makes this interesting. A lattice would make this trivial and unexportable.

---

## 2. The original setup (built from scratch)

### 2.1 Bone list

Eleven bones. Everything lives at or around the eye centre, which sits at `(1, -0.6053, 0)`. The character faces **-Y**, so the eye's forward direction is -Y and the stretch runs along the eye's depth.

| Bone | Parent | Job |
|---|---|---|
| `str_eye_roc.l` | — | **The rocker.** Sits at the eye centre. Rotating it swings the whole stretch mechanism, which is how you choose the stretch direction. |
| `str_eye_end.l` | `str_eye_roc.l` | Back handle. Sits at the back extreme of the eye. |
| `str_eye_start.l` | `str_eye_roc.l` | Front handle. Sits at the front extreme of the eye. |
| `str_eye.l` | `str_eye_end.l` | **The long bone.** Spans the eye from back to front. Carries the Stretch To. |
| `mch_str_eye_roc.l` | `str_eye_roc.l` | **The counter bone.** Driven to hold the exact opposite rotation of the rocker. |
| `eye.l` | `str_eye.l` | Eyeball deform bone. |
| `eye_T.l` | `str_eye.l` | Top eyelid deform bone. Points up and forward. |
| `eye_B.l` | `str_eye.l` | Bottom eyelid deform bone. Points down and forward. |
| `ctrl_eye.l` | — | Animator control for eye rotation. |
| `ctrl_eyelid_t.l` | — | Animator control for top lid. |
| `ctrl_eyelid_b.l` | — | Animator control for bottom lid. |

### 2.2 Constraints

- **`str_eye.l`** → Stretch To, targeting `str_eye_start.l`. Volume mode XZX, keep axis Swing Y.
- **`eye.l`** → Copy Rotation (Local→Local, Add) from `mch_str_eye_roc.l`; plus two Transform constraints reading `ctrl_eye.l`.
- **`eye_T.l`** → Copy Rotation (Local→Local, Add) from `mch_str_eye_roc.l`; Transform + Copy Rotation from `ctrl_eyelid_t.l`.
- **`eye_B.l`** → same pattern with `ctrl_eyelid_b.l`.

### 2.3 The drivers

Four drivers on `mch_str_eye_roc.l`'s rotation, one per quaternion channel:

- **W** → `-rotation_quaternion` reading `str_eye_roc.l`'s W
- **X, Y, Z** → straight copies of the rocker's X, Y, Z

All four use a plain linear mapping curve, so nothing gets clamped.

### 2.4 The reasoning behind it

The idea, step by step:

1. Put a rocker bone at the eye centre. Everything else hangs off it.
2. Put two handles at the front and back of the eye, both children of the rocker.
3. Run a long bone between them with a Stretch To. Move a handle in, the bone squashes. Move it out, it stretches.
4. Because the handles are children of the rocker, **rotating the rocker turns the whole stretch mechanism**. That's how you aim the squash.
5. Parent the eye and eyelids to the long bone, so they inherit the squash.
6. But they'd also inherit the rocker's rotation, which is not wanted — the eye should squash sideways without visually tumbling sideways.
7. So: build a counter bone that always holds the exact opposite rotation of the rocker, and have the eye and eyelids copy it. The two rotations cancel, leaving only the squash.

**This reasoning is correct.** That's worth saying clearly, because the rig had a visible bug and it would be easy to assume the whole approach was wrong. It wasn't.

### 2.5 About the negated W

The driver flips the sign on W only, leaving X, Y and Z alone. That looks like a shortcut but it genuinely produces the opposite rotation.

Think of a quaternion as storing two things: an axle to spin around, and how far to spin. X, Y and Z between them describe the axle. W describes how far. Flipping W's sign flips the spin direction while leaving the axle untouched — same axle, opposite way round.

There's a more conventional way to write it (flip X, Y and Z and leave W alone), and it produces an identical pose. The only practical difference is a sign flip on the stored value, which can matter if you're interpolating between two of them but doesn't matter here.

**Verified in-file:** with the rocker turned 40°, `mch_str_eye_roc.l` held perfectly still in world space. Measured change: **0.00°.** The counter bone worked exactly as designed.

---

## 3. What broke

### 3.1 Bug one — the eyelids drifted

**Symptom:** rotate the rocker, and the eyeball stays put correctly but the eyelids visibly tumble.

**Measurements.** Rocker turned 40° on three different axes; the numbers are unwanted world rotation on each deform bone (0° means perfect):

| Rocker turned on | `eye.l` | `eye_T.l` | `eye_B.l` |
|---|---|---|---|
| X | 0.00° | 0.00° | 0.00° |
| Y | 0.00° | **21.04°** | **25.43°** |
| Z | 0.00° | **21.04°** | **25.43°** |

So it worked on one axis and failed on the other two — and only for the eyelids.

**Cause.** Copy Rotation set to Local→Local copies the target's rotation *numbers* into the owner. Numbers, not direction.

An analogy. You and a friend are standing back to back. You say "turn 30° to your left." You both turn 30° to *your own* left — and end up facing completely different ways. Same instruction, different starting orientation, different result.

`mch_str_eye_roc.l` and `eye.l` are aimed the same way, so they interpret the same numbers identically and the cancellation is perfect. But `eye_T.l` is tilted **31.1°** away from the rocker's direction, and `eye_B.l` is tilted **37.8°** away. They're standing at a different angle, so the same numbers point them somewhere else.

Notice the error is bigger on `eye_B.l` (bigger tilt) than `eye_T.l` (smaller tilt). That's the fingerprint of this exact problem.

**Why one axis still worked.** The eyelids are tilted away from the rocker by a rotation around X. When the rocker also turns around X, the tilt and the turn share an axle, so the mismatch cancels out by luck. Turn the rocker around any other axis and there's no shared axle, so the error appears. This is why the bug hid for so long — the first axis anyone tests is usually the one that works.

### 3.2 Bug two — sliding a handle sideways rotates everything

**Symptom:** drag `str_eye_start.l` or `str_eye_end.l` off to the side, and the whole eye swings over. Nothing corrects it.

**Measurements.** Handle moved 0.4 sideways:

| Bone | Unwanted rotation |
|---|---|
| `str_eye.l` | −21.80° |
| `eye.l` | −21.80° |
| `eye_T.l` | −22.21° |
| `eye_B.l` | −22.33° |
| `mch_str_eye_roc.l` | **0.00°** — never reacted |

**Cause.** Stretch To quietly does two jobs, not one:

1. Change the bone's length to reach the target
2. **Turn the bone to point at the target**

Job two is the one that catches people out. Slide a handle along the line and only job one fires. Slide it sideways and job two fires — the long bone swings over to keep pointing at the handle, and everything parented underneath swings with it.

The counter bone never sees this because it's driven by the **rocker's rotation values**. It's watching the rocker's dial and nothing else. When a handle slides sideways, the rocker didn't move, so the dial reads zero, so the counter bone concludes nothing happened.

It's like someone watching your steering wheel to work out where the car is going. If a gust of wind shoves the car sideways, the wheel never turned, so they have no idea anything happened.

### 3.3 Bug three — Damped Track destroyed the squash

**Symptom:** add a Damped Track so the eye can lock onto a target, and the whole squash effect starts flailing around.

**Measurements.** With the eye squashed and the squash direction tilted, the look target was moved up and down. These numbers are the direction the eye is being flattened in:

| Look target | Damped Track directly on `eye.l` |
|---|---|
| centre | `0, 0.44, −0.90` |
| up | `0, 0.06, 1.00` |
| down | `0, 0.84, −0.54` |

The squash direction is being dragged all over the place by wherever the eye happens to be looking. It should not move at all.

**Cause — the playdough model.** This is the single most useful mental picture in the whole rig, so it's worth setting up properly.

Picture the eyeball as a ball of playdough, with a giant invisible hand squashing it flat from one side. There are two different moments where you could spin the ball:

**Moment one — spin it, then let the hand squash it.** The hand always squashes from the same direction. The ball spins freely inside. The flat side stays exactly where it is. The pupil slides across the flattened surface. *This is what a cartoon eye should do.*

**Moment two — let the hand squash it, then spin the pancake.** Now you're turning something that's already flat. The flat side turns with it. Look up, and the squash tilts up too. The effect falls apart.

The Transform constraints from `ctrl_eye.l` are set to **Local** space, which puts them at moment one. That's why they always behaved.

Damped Track has **no Local option**. It only knows how to grab the finished bone and turn it to face the target. "Finished" means after the squash has already been applied. So it always lands at moment two.

**Damped Track is not broken. It was standing in the wrong place in the queue.**

### 3.4 A wrong fix worth knowing about

The obvious repair for a bone rotating when it shouldn't is to lock its orientation with a World-space Copy Rotation. This was tested and it **breaks the rig**:

| | Squash lean | Bone scale |
|---|---|---|
| Local-space counter (correct) | −0.639 | 1.291 / 0.949 / 1.291 |
| World-space Copy Rotation | **0.000** | 1.291 / **0.600** / 1.291 |

That second row looks *cleaner*, and that's the trap. World-space constraints pull the bone apart into position/rotation/scale, swap the rotation, and rebuild it. That rebuild can't represent a lean, so the lean is thrown away. The eye then squashes along its own axis and ignores the rocker completely.

**Rule of thumb: World-space constraints flatten a bone's transform. If your rig depends on a lean, don't put one downstream of the thing creating it.**

### 3.5 The lean, and why it isn't a bug

While debugging, one thing looks alarming and is actually correct. Once the eye is squashed at an angle, `eye.l` reports its scale as **1.291 / 0.949 / 1.062** even though its parent is scaled 1.291 / 0.600 / 1.291. The bone also draws visibly skewed in the viewport, and reports about 1° of rotation that nobody asked for.

Nothing is wrong. Squashing something along a direction that doesn't line up with the bone's own axes produces a **lean** — the bone's axes stop being at right angles to each other. Blender's readout can only describe position, rotation and scale, so it has nowhere to put the lean and smears it across the rotation and scale figures instead.

The actual deformation was checked directly against the intended result. **Difference: 0.00000.** The readout is misleading; the deformation is exact.

If you're debugging a squash rig and the numbers look wrong, check the mesh, not the panel.

---

## 4. The fixes

Both fixes are the same move in different clothing:

> **Do the clean work on a separate bone that nothing is squashing, then hand the result across in Local space.**

That's what machine bones are for in every production rig.

### 4.1 Fix one — `mch_unrot.l`

Instead of asking three differently-aimed bones to each undo the rotation for themselves, one bone undoes it once and the others sit underneath it.

**Build:**

1. In Edit Mode, duplicate `mch_str_eye_roc.l` and rename to **`mch_unrot.l`**. Duplicating matters — it inherits the rocker's exact orientation and pivot, which is the whole point.
2. Parent it to **`str_eye.l`**. It sits *inside* the stretch, so it still receives the squash.
3. Give it one constraint: **Copy Rotation, Local → Local, Replace**, targeting `mch_str_eye_roc.l`.
4. Re-parent `eye.l`, `eye_T.l` and `eye_B.l` to `mch_unrot.l`.
5. Delete the old Copy Rotation constraints from all three. Leave the Transform and lid constraints alone.
6. Optionally put `mch_unrot.l` and `mch_str_eye_roc.l` on an `MCH` bone collection so you can hide them.

**Why it works.** `mch_unrot.l` is aimed identically to the rocker, so the numbers mean the same thing in both bones and the cancellation is exact. The three deform bones then inherit a frame that has *already* been corrected, so their own orientations stop mattering entirely.

**Result:**

| Rocker turned on | Before | After |
|---|---|---|
| X | 0° / 0° / 0° | 0° / 0° / 0° |
| Y | 0° / **21.04°** / **25.43°** | 0° / **0°** / **0°** |
| Z | 0° / **21.04°** / **25.43°** | 0° / **0°** / **0°** |

Three constraints removed, one bone and one constraint added, and it now works on every axis instead of one.

### 4.2 Fix two — `mch_eye_aim.l`

Move Damped Track somewhere the squash can't reach it.

**Build:**

1. In Edit Mode, duplicate `eye.l` and rename to **`mch_eye_aim.l`**. Same orientation, same pivot.
2. **Parent it outside the stretch chain.** In a real character, parent it to the head bone. Nothing squashes it.
3. Add a bone called **`ctrl_lookat.l`** floating in front of the face. This is the look target. Parent it to the root, not the head, so the eyes stay locked on when the head moves.
4. Put the **Damped Track** on `mch_eye_aim.l`, targeting `ctrl_lookat.l`, track axis Y.
5. On `eye.l`, add **Copy Rotation, Local → Local, Replace**, reading `mch_eye_aim.l`. Name it `Aim` and **move it to the top of the stack** so the `ctrl_eye.l` controls still stack on top as a manual offset.

**Why it works.** The aiming happens on a clean bone with no squash on it. Handing the result over in Local space slides it back into *moment one* — before the hand squashes. The eyeball spins inside a shell that stays flattened in whatever direction the rocker set.

**Result:**

| Look target | Damped Track on `eye.l` | Aim bone method |
|---|---|---|
| centre | `0, 0.44, −0.90` | `0, 0.77, −0.64` |
| up | `0, 0.06, 1.00` | `0, 0.77, −0.64` |
| down | `0, 0.84, −0.54` | `0, 0.77, −0.64` |

Squash direction: dead still across every look direction. Squash amount: 0.600 in all three cases.

### 4.3 Fix three — the sideways handle

This one is a design decision, not a repair.

**Option A — lock it out.** Restrict the handle bones so they can only slide along their own axis. The swing becomes impossible and the rocker stays the only thing that sets direction. Simple, predictable, and what most production rigs would do.

**Option B — keep it.** A handle that tilts the eye when dragged sideways is a perfectly usable animator control. There's nothing broken about it as long as it's intentional and documented.

**Option C — the hard road.** Drive the counter bone from a Transform Channel driver reading the long bone's *actual final rotation* rather than the rocker's dial. Transform Channel variables read the result after constraints have run, so this would catch the Stretch To swing as well as the rocker. It also brings dependency-loop risk and gimbal headaches. Not recommended until everything else is solid.

---

## 5. Export — short version

The rig exports correctly. It was tested by actually exporting to GLB, re-importing, and comparing the deformed mesh vertex by vertex. Worst error was about one and a half **millionths** of the eye's diameter.

But there is a trap in it that is worth understanding properly, because it is the exact opposite of what normal rigging instinct tells you. **Sections 6 to 9 cover this in full**, from the ground up. If you only read one part of this document later, read those.

Quick checklist for shipping:

- Parent the meshes to the armature (`Ctrl+P → Object (Keep Transform)`). An Armature modifier alone is not enough — the exporter warns about it.
- **Do not tick "Deformation Bones Only"** in the glTF exporter. Explained in section 8.
- Non-uniform bone scale is the real compatibility risk. Unity has historically handled it badly on skeletons; Unreal is more tolerant. Test in your target engine early.
- Drivers and constraints do not survive export. Only the baked result does. Confirm your baking is actually sampling the driven bones.

---

## 6. Understanding "lean" — the concept a TA needs

This is the most transferable idea in the whole project. It has nothing to do with eyes specifically. It shows up in stretchy limbs, squashy props, cartoon jaws, anything where scaling and rotating meet. Learn it once and it pays off forever.

### 6.1 What a bone is allowed to say

A bone can only describe three kinds of change to the mesh:

1. **Move it** — shift it somewhere else.
2. **Turn it** — rotate it.
3. **Stretch it** — make it bigger or smaller along the bone's own three directions.

That word "own" is important. Every bone has three invisible arrows sticking out of it: one along its length, one across its width, one through its depth. Scaling stretches along *those arrows*, not along world X/Y/Z.

And here's the rule that matters: **those three arrows are always at right angles to each other.** Rotating the bone swings all three together, so they stay square. Scaling makes them longer or shorter, but they stay square. Nothing a single bone can do will make them stop being square.

### 6.2 What a lean actually is

Picture a cardboard box sitting on a table.

- Slide it across the table — that's **moving**.
- Spin it around — that's **turning**.
- Make it taller, or wider — that's **stretching**.

Through all of that, the corners of the box stay square. Ninety degrees everywhere.

Now put your hand on the top of the box and push it sideways while the bottom stays stuck to the table. The box goes slanted, like a stack of books pushed over. The corners are no longer square — the top face has slid sideways relative to the bottom.

**That is a lean.** The technical name is *shear*, but "lean" describes it better.

And here's the part to sit with: **you cannot get a leaning box by moving, turning, and stretching a square box.** Try it in your head. Turn it any way you like, stretch it any way you like — the corners stay square. Leaning is a genuinely different, fourth kind of change. A bone has no slot for it.

### 6.3 Why this rig produces one

Draw a circle on a sheet of rubber. Through the middle, draw a cross — one line horizontal, one vertical, meeting at a perfect right angle.

Now grab the rubber sheet and squash it **diagonally**, at 45° to your cross.

Two things happen:

- The circle becomes an oval. Expected, fine.
- **The cross stops being square.** The two lines lean toward each other. They're no longer at ninety degrees.

That cross is the bone's three arrows. The diagonal squash is your rocker.

The eye bone points whichever way it points. The animator squashes along whatever direction the rocker is set to. When those two directions don't line up, **the bone's arrows stop being square** — and now the bone is carrying something it has no slot for.

This is not a bug. It is the correct and necessary shape of the deformation. Squashing a shape along an angle it isn't aligned with *is* a lean. There is no way to do that effect without one.

### 6.4 Why Blender's readout appears to lie

Blender's N-panel has exactly three boxes: position, rotation, scale. That's the whole vocabulary.

So when a bone is leaning, Blender is being asked to describe a slanted box using only "where, which way, how big." It can't. So it gives you the closest square-cornered box it can find, and the numbers come out strange:

| | Reported |
|---|---|
| `str_eye.l` actual scale | 1.291 / 0.600 / 1.291 |
| `eye.l` reported scale | 1.291 / **0.949** / **1.062** |
| `eye.l` reported rotation | about 1°, from nowhere |

Looks broken. The mesh was checked directly against the intended deformation: **difference 0.00000**. The deformation is exact. The panel is just answering a question it doesn't have the words for.

> **Rule: if a squash rig's numbers look wrong, check the mesh, not the panel.** The panel cannot describe a lean, so it will always look wrong.

### 6.5 The idea that makes export possible

Here is the part that ties everything together.

**A lean cannot be stored in one bone — but it can be built out of two clean ones.**

Back to the box. Take a perfectly square box:

1. Turn it 45°.
2. Now squash it straight down.

Neither step was a lean. Step one was pure turning. Step two was pure stretching. But **the result is a slanted shape.** Two square-cornered operations, stacked, produced something that leans.

That's the whole trick. A lean can be manufactured out of clean pieces.

And that's exactly how this rig is built:

| Bone | What it holds | Leaning? |
|---|---|---|
| `str_eye.l` | a pure stretch | no |
| `mch_unrot.l` | a pure turn | no |
| `eye.l` | a turn plus an offset | no |

**Not one bone in the chain is leaning.** The lean only exists once you stack all three together — and that stacking happens when the engine draws the frame, not when the file is written.

---

## 7. What the export test actually measured

Two separate tests were run in the file. Both used the same method: pose the rig, bake, export to GLB, re-import, compare against the source.

### 7.1 Test one — the chained rig

The rig was animated from rest to fully squashed (rocker turned 40°, squash at 0.6, eye looking up), exported with baked animation, re-imported, and the deformed mesh was compared vertex by vertex at four points through the animation.

| Frame | Max deviation | Mean deviation |
|---|---|---|
| 1 (rest) | 0.0000011 | 0.0000004 |
| 10 | 0.0000013 | 0.0000006 |
| 15 | 0.0000015 | 0.0000006 |
| 20 (full squash) | 0.0000010 | 0.0000004 |

The eye is 1.0 units across. Worst error is roughly **one and a half millionths** of the eye's diameter — that is the rounding error of the file format, not rig breakage.

Bone transforms matched to the same precision. The re-imported armature reported `str_eye.l` scale as 1.291 / 0.600 / 1.291 at frame 20, identical to the source.

**Why it survived.** GLB stores each bone as position + rotation + scale *relative to its parent*, and stores the whole family tree. It cannot store a lean — but it never had to, because no single bone in this rig is leaning. The engine multiplies the chain back together at runtime and the lean reassembles on the far side.

### 7.2 The correction to the original assumption

The working assumption going in was: *"non-uniform scale only breaks export if the scaled bone has children."*

That is close to the real rule but backwards in an important way. In this rig, `str_eye.l` carries the non-uniform scale and **does** have children, two levels deep — and it exported perfectly.

The real rule is:

> **Each bone's own transform, relative to its parent, must be describable as position + rotation + scale. If it is, it exports. If it isn't, it doesn't.**

Children are not the problem. Children are the **solution**.

---

## 8. The DEF-bone trap

This is the counterintuitive part, and the most valuable thing in this document for a TA.

### 8.1 The plan that seemed obviously right

Standard production structure: a clean DEF layer with only the bones that actually deform mesh, parented straight to root or head, carrying no constraints of their own, with all the machinery hidden in ORG and MCH layers above.

For this rig that would mean four exported bones: `root`, `DEF_eye.l`, `DEF_eye_T.l`, `DEF_eye_B.l`. Each DEF bone gets a Copy Transforms from its ORG counterpart. Clean, minimal, no children anywhere. Textbook.

### 8.2 It was built and tested. It breaks.

| Bone | Lean in Blender | Lean after export | Error |
|---|---|---|---|
| `DEF_eye.l` (parented to root) | 0.639 | **0.000** | 0.361 |
| `DEF_eye_T.l` | 0.494 / −0.259 / 0.267 | **0.000** | 0.336 |
| `DEF_eye_B.l` | 0.440 / 0.316 / −0.290 | **0.000** | 0.331 |
| `eye.l` (still in the chain) | 0.639 | 0.639 | **0.000** |

Error of 0.33 to 0.36 on an eye 1.0 across. The angled squash is simply gone. In the engine you would get a squash along the bone's own axis no matter where the rocker was pointing.

**The nastiest part: it looked perfect in Blender.** Copy Transforms copies the bone's transform wholesale — lean included — so the viewport showed the correct result right up until export. This is the kind of bug that ships.

### 8.3 Why it breaks

Go back to the box.

In the chained version, the lean is built in stages: one bone turns, the next stretches, the next turns back. Each stage is square-cornered on its own. GLB writes down the stages and the engine performs them in order.

Flatten it to a single DEF bone hanging off root, and that one bone now has to hold the **finished slanted shape** all by itself. There are no stages left. And a single bone has only three slots — where, which way, how big. Nowhere to put the lean.

So the exporter does the only thing it can: it finds the closest square-cornered approximation and throws the rest away.

> **The chain was never a liability. The chain was the delivery mechanism.**

### 8.4 The hierarchy that actually works

You cannot get to four bones. Six is the minimum:

```
root  (or head)
└── DEF_stretch.l      ← carries the squash and the rocker's direction
    └── DEF_unrot.l    ← undoes the rocker's rotation
        ├── DEF_eye.l
        ├── DEF_eye_T.l
        └── DEF_eye_B.l
```

The three deform bones still have no children, which was the actual goal. The two bones above them are pure plumbing — untick Deform on both. They exist only so the engine has the stages to multiply.

The DEF layer still works exactly as intended otherwise: one Copy Transforms per DEF bone from its matching ORG/MCH counterpart, nothing else below. Those two levels just can't be collapsed out.

### 8.5 The landmine

In the glTF exporter, **do not tick "Deformation Bones Only."**

It strips non-deform bones from the exported skeleton. That would remove `DEF_stretch.l` and `DEF_unrot.l` and silently reintroduce the exact failure measured above — and it would still look perfect in Blender.

Either leave that option off, or mark those two bones as deform bones carrying no weights.

---

## 9. Diagnostic toolkit

Everything above, reduced to things you can actually run and check.

### 9.1 Symptoms that point at a lean problem

- The effect looks right in Blender and wrong in the engine.
- A bone's scale readout doesn't match its parent's scale, and neither number makes sense.
- A bone reports a small rotation that nothing is driving.
- Bone octahedrons draw visibly skewed in the viewport.
- Adding a World-space constraint makes the numbers look *cleaner* and the result look *worse*.

That last one is the giveaway. Cleaner numbers plus worse result almost always means something just got flattened.

### 9.2 Is this bone leaning?

The bone's three arrows should be at right angles. This measures how far off they are — `0.0` means perfectly square, anything else is a lean.

```python
import bpy

pb = bpy.context.active_pose_bone
m = pb.matrix.to_3x3()
c = [m.col[i].normalized() for i in range(3)]
print("x-y:", round(c[0].dot(c[1]), 4))
print("x-z:", round(c[0].dot(c[2]), 4))
print("y-z:", round(c[1].dot(c[2]), 4))
```

A lean isn't automatically a problem. What matters is whether it lives in a single bone's own transform, which is the next check.

### 9.3 Will this rig export? — the important one

This does exactly what the exporter does: takes each bone's transform relative to its parent, pulls it apart into position/rotation/scale, rebuilds it, and reports what got lost. Run it on a **posed** rig, in its most extreme pose.

```python
import bpy
from mathutils import Matrix

ob = bpy.context.object
problems = []

for pb in ob.pose.bones:
    parent = pb.parent.matrix if pb.parent else Matrix.Identity(4)
    local = parent.inverted() @ pb.matrix
    loc, rot, scale = local.decompose()
    rebuilt = Matrix.LocRotScale(loc, rot, scale)
    err = max(abs(local[r][c] - rebuilt[r][c])
              for r in range(4) for c in range(4))
    if err > 1e-5:
        problems.append((pb.name, err))

if problems:
    for name, err in problems:
        print(f"WILL NOT EXPORT CLEANLY: {name}  (loses {err:.4f})")
else:
    print("All bones export cleanly.")
```

Anything this flags will lose data on export no matter which format you use. It is not a Blender limitation or a glTF limitation — position/rotation/scale is how every mainstream engine stores bones.

**Run this before you rig the rest of the character, not after.**

### 9.4 How constraints treat a lean

All of these were measured in this file, not assumed.

| Constraint | What it does to the transform | Effect on a lean |
|---|---|---|
| Copy Rotation, **Local** space | works on the bone's own channel, before the parent's scale is applied | **safe** — there is no lean there yet to damage |
| Copy Rotation, **World** space | pulls the finished transform apart, swaps the rotation, rebuilds it | **destroys it** |
| Copy Transforms, World space | copies the transform wholesale | preserves it |
| Transform constraint, Local space | works on the bone's own channel | **safe** |
| Damped Track | multiplies a rotation onto the outside of the finished transform | preserves the lean, but applies the rotation **after** the squash — see section 3.3 |

Two separate questions hide in that table, and mixing them up causes a lot of confusion:

1. **Does the constraint preserve the lean?** Copy Rotation in World space does not. Copy Transforms does.
2. **Does it act before or after the squash?** Local space acts before. Damped Track acts after.

A constraint can pass one test and fail the other. Damped Track preserves the lean perfectly and still ruins the rig, because it lands at the wrong moment.

### 9.5 Rules worth memorising

- **Position, rotation and scale are the only three things a bone can say.** Anything else has to be built out of a chain.
- **A lean can be manufactured from clean pieces.** Turn, then stretch. Neither leans; the result does.
- **Files store the pieces, not the result.** So keep the pieces clean and let the engine do the multiplying.
- **Flattening a hierarchy is not always safe.** If an effect depends on stacking, collapsing it destroys the effect.
- **World space means "pull apart and rebuild."** Anything that can't be rebuilt from position/rotation/scale gets thrown away.
- **Cleaner numbers, worse result** = something just got flattened. Go and find what.
- **Test the export early.** Export, re-import, compare. Ten minutes at the start beats a rebuild at the end.

### 9.6 The round-trip test

The only test that actually proves anything. Worth turning into a reusable script.

1. Pose the rig into its most extreme, most unreasonable pose.
2. Keyframe rest → extreme over 20 frames.
3. Export to GLB with animation baked.
4. Import the GLB straight back into the same file.
5. Compare the deformed meshes at several frames — nearest-neighbour distance between the two vertex clouds.
6. Compare bone transforms too, since a mesh can look fine while the skeleton is subtly wrong.

Anything under roughly `1e-5` relative to the model's size is float rounding. Anything above that is real, and you should find out why before building anything else on top of it.

---

---

## 10. Tutorial structure suggestion

The debugging story is more valuable than the build. Most rigging tutorials show a finished rig assembled perfectly; almost none show a working rigger finding and fixing their own mistake. Lead with that.

Suggested flow:

1. **Cold open** — the finished rig doing its thing. Eye stretching, pupil sliding across the flattened surface, lids following.
2. **Why not a lattice** — the export constraint. Sets up the whole problem.
3. **Build the mechanism** — rocker, handles, long bone, Stretch To.
4. **The rotation problem** — parent the eye, show it tumbling. Explain why.
5. **The counter bone** — drivers, the negated W, what a quaternion is storing in plain language.
6. **The bug** — rotate on the other axis, eyelids drift. Sit with it. Don't cut to the fix immediately.
7. **The back-to-back analogy** — why the same numbers mean different things to differently-aimed bones.
8. **Fix one** — `mch_unrot.l`.
9. **The Damped Track trap** — try it, watch the squash flail.
10. **The playdough model** — moment one versus moment two.
11. **Fix two** — `mch_eye_aim.l`.
12. **Export** — bake, GLB, check it in an engine.
13. **Closing thought** — when a constraint "messes everything up," ask *when* it runs before asking *what* it does.

---

## 11. YouTube package

### 11.1 Title options

Ranked, with reasoning.

**1. `Cartoon Eye Rig in Blender — Squash & Stretch WITHOUT a Lattice (Game Engine Ready)`**
Best all-rounder. Front-loads the searchable terms, and "without a lattice" is the hook — it names a constraint people actually search for. "Game Engine Ready" catches the export crowd.

**2. `I Broke My Own Eye Rig — and the Fix Was Rig 101`**
Highest click-through, lowest search traffic. Great as a second upload or a Short. Curiosity gap plus humility, which performs well with intermediate riggers.

**3. `Blender Cartoon Eye Rig: Stretchy Eyes That Still Look Around`**
Cleanest description of the actual feature. "Still look around" targets the specific pain point of the eyeball popping through the lids.

**4. `Why Damped Track Breaks Your Squash & Stretch Rig (Blender)`**
Narrow but potent. This is an unanswered search query and the video would likely own it. Good candidate for a standalone follow-up.

**5. `Exportable Cartoon Eye Rig — No Lattice, No Shape Keys, Just Bones`**
Strong for the game-dev audience specifically.

**Recommendation:** go with **#1** as the main title. Keep **#4** in your back pocket as a separate short video pointing back at this one — that's cheap cross-linking on a query with no competition.

### 11.2 Description

```
A fully stretchable cartoon eye rig in Blender — built with nothing but bones, so it
exports straight to GLB or FBX for Unreal, Unity or Godot. No lattice. No mesh deformers.
No shape keys.

The eye squashes and stretches in any direction you choose, and the eyeball still rotates
INSIDE the deformed shape instead of popping through the eyelids like a rigid sphere.

This isn't a clean walkthrough of a finished rig. I built it, it half-worked, and I spent
a while finding out why. The two bugs turned out to have the same cause — and the same
fix — so you get the debugging as well as the build.

What you'll learn:
- Building a stretch mechanism with a rocker bone and two handles
- Using drivers to build a counter-rotation bone
- Why Copy Rotation in Local space copies NUMBERS, not directions
- The hidden second job that Stretch To performs
- Why Damped Track destroys squash and stretch, and where to put it instead
- Why World-space constraints quietly flatten your rig
- Keeping the whole thing exportable

Chapters below. Blend file linked if you want to poke at it yourself.

---
CHAPTERS
00:00  What we're building
00:00  Why not just use a lattice
00:00  Rocker, handles and the long bone
00:00  Stretch To setup
00:00  The rotation problem
00:00  Building the counter bone with drivers
00:00  What the negated W actually does
00:00  The bug: eyelids drifting
00:00  Why the same numbers mean different things
00:00  Fix 1: the un-rotator bone
00:00  Trying Damped Track (and watching it break)
00:00  The playdough model
00:00  Fix 2: the aim bone
00:00  The sideways handle problem
00:00  Exporting to GLB
00:00  What I'd tell past me

---
Blender 5.2

I'm Ade David — 3D artist working toward technical art, rigging and tools. New videos on
rigging, Blender Python and character setup.

Subscribe: [link]
Blend file: [link]
Instagram / ArtStation: [links]

#blender #rigging #b3d #technicalart #gamedev #characterrigging
```

### 11.3 Tags

```
blender rigging, cartoon eye rig, squash and stretch, blender eye rig, character rigging,
blender tutorial, technical artist, rigging tutorial, blender constraints, damped track,
stretch to constraint, blender drivers, game engine rigging, glb export, blender 5.2,
exportable rig, b3d, eye rig tutorial, cartoon rigging, blender bones
```

### 11.4 Thumbnail

Split frame. Left: eye at rest, normal and round. Right: same eye stretched hard at an angle with the pupil clearly sitting on the flattened surface. Big arrow between them.

Overlay text — pick one, keep it to three or four words:

- **NO LATTICE**
- **STRETCHY EYES**
- **BONES ONLY**

Small corner badge: `GLB READY` or `EXPORTABLE`.

Your face is optional but helps on the debugging-story version. If you use it, an honest "what have I done" expression fits the content better than an exaggerated shocked face.

### 11.5 Pinned comment

```
Quick note on the two bugs in this video — they turned out to be the same mistake wearing
two different costumes.

Both times, a constraint was sitting somewhere it got squashed or rotated by something
upstream. Both times, the fix was the same: do the clean work on a separate bone that
nothing is deforming, then hand the result over in Local space.

If a constraint is "messing everything up," ask WHEN it runs before you ask WHAT it does.
Order of operations breaks more rigs than wrong settings do.

What would you have done differently? Genuinely curious — there's more than one way to
solve the sideways handle problem and I only picked one.
```

### 11.6 Extra content from the same material

- **Short (under 60s):** just the playdough explanation. Squash-then-spin versus spin-then-squash, with the rig showing both. Strong standalone hook.
- **Short:** the eyelid bug — rotate on X, works; rotate on Z, drifts. "Same constraint. Same settings. Different result. Here's why."
- **Follow-up video:** `Why Damped Track Breaks Your Squash & Stretch Rig`. Ten minutes, links back to the full build.
- **Community post:** screenshot of the constraint stack, ask people to spot the problem before the video drops.

---

## 12. Two lessons to carry forward

**On building rigs:**

> **Do the clean calculation on a bone that nothing is deforming, then pass the result across in Local space.**

That's what `mch_unrot.l` does for the rocker's rotation, and what `mch_eye_aim.l` does for the look direction. Same idea both times, and it's most of what machine bones exist for.

The matching diagnostic habit: when a constraint "messes everything up," ask **when** it runs before you ask **what** it does. Order of operations breaks more rigs than wrong settings do.

**On exporting rigs:**

> **A bone can only say where, which way, and how big. Anything more complicated has to be built out of a chain — and the chain has to survive the export.**

This one runs against normal instinct. Everything in production rigging pushes you toward flatter, cleaner deform hierarchies. Usually that's right. But when an effect is *manufactured* by stacking transforms, flattening it destroys the very thing you built.

The tell is brutal and worth memorising: **it looks perfect in Blender right up until it doesn't.** Copy Transforms carries the lean happily inside Blender and loses it the moment it's written to a file. Nothing warns you. The only defence is to export, re-import, and measure — early, before anything else is built on top.
