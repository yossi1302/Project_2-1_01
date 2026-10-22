# Project_2-1_01

This project involves the creation of a program which uses eye tracking to create a parallax effect on the user's screen, making it seem as though they are looking through a window.  For this, we used the Python language as well as these following libraries:

- OpenCV for webcam capture
- Mediapipe for the face landmark model
- Panda3D for rendering the 3D scene
- Flet for the GUI

## Running the demo

1. Create a virtual environment for Python: `python -m venv <path to venv>`
2. Activate the virtual environment
3. Install the required libraries: `pip install -r requirements.txt`
4. Run the demo: `python demo.py`

## Main components

The program is made up of a number of interconnected components:

- The eye tracker
- The renderer
- Projection math functions
- The GUI

## Data flow

The inputs to the program are the webcam steam from OpenCV and the face landmark model. These both are fed into Mediapipe to generate a list of landmarks, which contain many features, including the iris center points which we are especially interested in.

From these points we pick out the two iris points. We can use these to estimate the direction the user is looking towards. The distance between the eyes can be used to calculate the distance from the webcam, since the eyes appear closer together as the user leans away.

This eye position is used in the off-axis projection calculations. This projection is appropriate for approximating the way the image would change if the user did actually look through a window. The calculations are then used to configure the Panda3D camera and Lens objects, which are used in the renderer.

The Panda3D scene is prepared with a tree of objects we prepared in advance. This will act as the scene on the other side of the metaphorical window. This is combined with the off-axis projection to create frames rendered into an off-screen pixel buffer.

We use an off-screen buffer since we are using a Flet GUI instead of a native Panda3D window. The Flet GUI uses a RawImage component which we can provide with a numpy array containing the pixel data. Every time a frame is rendered, which happens on a timer about 60 times per second, the image data from the frame is pushed to this Flet component.

The webcam source is also sampled regularly and pushed to its own Flet RawImage component. This makes the bulk of our GUI at the moment, though in the future we will add more settings and some metrics showing what the program is doing at any moment.

## Future plans

For the future, we plan to improve the existing components and add some more features which would allow greater control and introspection into the program. We would also like to improve the default scene and provide other options for the illusion that is used.

