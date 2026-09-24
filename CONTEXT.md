# Parallax viewer tracking

This context defines the language used for locating the viewer in front of the display. It does not describe gaze estimation or the later graphics implementation.

## Language

**Viewer-position tracking**:
Estimating the three-dimensional location of one viewer's eye midpoint relative to the camera.
_Avoid_: Eye tracking, gaze tracking

**Eye midpoint**:
The point halfway between the estimated centers of the viewer's left and right eyes.
_Avoid_: Gaze point, pupil position

**Gaze tracking**:
Estimating where a viewer is looking. This is outside the project scope because the parallax effect depends on viewer position, not gaze direction.
_Avoid_: Viewer-position tracking

**Test condition**:
A labelled segment in the guided recording that changes one relevant factor, such as illumination, glasses, occlusion, distance, or head rotation.
_Avoid_: Test case

**Reference-distance calibration**:
A reserved segment at the start of the guided recording, made at a measured camera distance. Each tracking method uses its median detected eye separation as the pixel baseline for relative depth scaling. Those frames are excluded from evaluation.
_Avoid_: Interpupillary-distance calibration, test condition

**Detection success**:
The proportion of input frames for which a method returns a valid pair of eye centers.
_Avoid_: Accuracy

**Tracking latency**:
The wall-clock time from providing a decoded frame to receiving that method's tracking result.
_Avoid_: End-to-end latency

**Stationary jitter**:
The variation in estimated viewer position while the viewer and camera remain still.
_Avoid_: Accuracy, noise
