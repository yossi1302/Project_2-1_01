from panda3d.core import lookAt
from panda3d.core import GeomVertexFormat, GeomVertexData
from panda3d.core import Geom, GeomTriangles, GeomVertexWriter
from panda3d.core import Texture, GeomNode
from panda3d.core import PerspectiveLens
from panda3d.core import Light, Spotlight
from panda3d.core import TextNode
from panda3d.core import LVector3
from panda3d.core import RenderState, TextureAttrib

def normalized(*args):
    myVec = LVector3(*args)
    myVec.normalize()
    return myVec

def make_square(texture_path, x1, y1, z1, x2, y2, z2):
    format = GeomVertexFormat.getV3n3cpt2()
    vdata = GeomVertexData('square', format, Geom.UHDynamic)

    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')
    texcoord = GeomVertexWriter(vdata, 'texcoord')

    # make sure we draw the sqaure in the right plane
    if x1 != x2:
        vertex.addData3(x1, y1, z1)
        vertex.addData3(x2, y1, z1)
        vertex.addData3(x2, y2, z2)
        vertex.addData3(x1, y2, z2)

        normal.addData3(normalized(2 * x1 - 1, 2 * y1 - 1, 2 * z1 - 1))
        normal.addData3(normalized(2 * x2 - 1, 2 * y1 - 1, 2 * z1 - 1))
        normal.addData3(normalized(2 * x2 - 1, 2 * y2 - 1, 2 * z2 - 1))
        normal.addData3(normalized(2 * x1 - 1, 2 * y2 - 1, 2 * z2 - 1))

    else:
        vertex.addData3(x1, y1, z1)
        vertex.addData3(x2, y2, z1)
        vertex.addData3(x2, y2, z2)
        vertex.addData3(x1, y1, z2)

        normal.addData3(normalized(2 * x1 - 1, 2 * y1 - 1, 2 * z1 - 1))
        normal.addData3(normalized(2 * x2 - 1, 2 * y2 - 1, 2 * z1 - 1))
        normal.addData3(normalized(2 * x2 - 1, 2 * y2 - 1, 2 * z2 - 1))
        normal.addData3(normalized(2 * x1 - 1, 2 * y1 - 1, 2 * z2 - 1))

    texcoord.addData2f(0.0, 1.0)
    texcoord.addData2f(0.0, 0.0)
    texcoord.addData2f(1.0, 0.0)
    texcoord.addData2f(1.0, 1.0)

    # Quads aren't directly supported by the Geom interface
    # you might be interested in the CardMaker class if you are
    # interested in rectangle though
    tris = GeomTriangles(Geom.UHDynamic)
    tris.addVertices(0, 1, 3)
    tris.addVertices(1, 2, 3)

    square = Geom(vdata)
    square.addPrimitive(tris)

    return square

def add_cube(render, texture_path):
    tex1 = Texture("Texture")
    tex1.setup2dTexture()
    tex1.read(texture_path)
    tex1.setMagfilter(Texture.FTNearest)
    tex1.setMinfilter(Texture.FTNearest)
    state_a = RenderState.make(TextureAttrib.make(tex1))

    # Note: it isn't particularly efficient to make every face as a separate Geom.
    # instead, it would be better to create one Geom holding all of the faces.
    square0 = make_square(texture_path, -1, -1, -1, 1, -1, 1)
    square1 = make_square(texture_path, -1, 1, -1, 1, 1, 1)
    square2 = make_square(texture_path, -1, 1, 1, 1, -1, 1)
    square3 = make_square(texture_path, -1, 1, -1, 1, -1, -1)
    square4 = make_square(texture_path, -1, -1, -1, -1, 1, 1)
    square5 = make_square(texture_path, 1, -1, -1, 1, 1, 1)
    snode = GeomNode('square')
    snode.addGeom(square0, state_a)
    snode.addGeom(square1, state_a)
    snode.addGeom(square2, state_a)
    snode.addGeom(square3, state_a)
    snode.addGeom(square4, state_a)
    snode.addGeom(square5, state_a)

    cube = render.attachNewNode(snode)
    cube.hprInterval(1.5, (360, 360, 360)).loop()

    # OpenGl by default only draws "front faces" (polygons whose vertices are
    # specified CCW).
    cube.setTwoSided(True)
    return cube


def load_example(render):
    cube1 = add_cube(render, "./assets/example1.png")
    cube1.setPos(10, 0, 8)
    cube2 = add_cube(render, "./assets/example2.png")
    cube2.setPos(-8, 2, -2)
    cube3 = add_cube(render, "./assets/example2.png")
    cube3.setPos(11, 4, -2)
    cube3.setScale(2)

