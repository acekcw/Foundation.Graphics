
from OpenGL.GL import *
from OpenGL.GL.shaders import *
from imgui.integrations.glfw import GlfwRenderer

import glfw
import glm
import math
import imgui

import numpy as np
import freetype as ft


vertexShaderCode = """

# version 330 core

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec4 aColor;

out vec4 color;

uniform mat4 prjMat;
uniform mat4 viewMat;
uniform mat4 modelMat;

void main()
{
    gl_Position = prjMat * viewMat * modelMat * vec4(aPos, 1.0);

    color = aColor; 
    
    // gl_Position = prjMat * viewMat * vec4(aPos, 1.0);
    // gl_Position = vec4(aPos, 1.0);
}

"""

fragmentShaderCode = """

# version 330 core

in vec4 color;

out vec4 fragColor;

uniform vec4 uniformColor;
uniform bool useUniformColor;

void main()
{
    if (useUniformColor)
    {
        fragColor = uniformColor;
    }
    else
    {
        fragColor = color;
    }
}

"""


class Index:
    SPECIFIC_PROGRAM_INFO_COLOR = 0
    SPECIFIC_PROGRAM_INFO_TEXT_POS = 1
    SPECIFIC_PROGRAM_INFO_TEXT_INTERVAL = 2
    SPECIFIC_PROGRAM_INFO_NUM_TEXTS = 3
    SPECIFIC_PROGRAM_INFO_FONT_SIZE = 4
    SPECIFIC_PROGRAM_INFO_TEXT_0 = 5   

class SceneManager:
    def __init__(self, view3D):
        self.displaySize = (800, 600)
        self.screenSize = (560, 560)        
        self.screenPos = []

        self.drawingStuffVerticesList = []
        self.drawingStuffIndicesList = []

        self.coordAxesVertices = []
        self.coordAxesIndices = []

        self.programInfoAreaVertices = []
        self.programInfoAreaIndices = []

        self.fovy = 45.0
        self.aspect = self.screenSize[0] / self.screenSize[1]
        self.near = 0.1
        self.far = 1000.0

        self.shader = None

        self.camera = None
        self.sailingCamera = [False, False]

        self.view3D = view3D
        self.drawAxes = True

        self.perspectivePrjMat = glm.perspective(self.fovy, self.aspect, self.near, self.far)
        self.orthoPrjMat = glm.ortho(0, self.displaySize[0], 0, self.displaySize[1], 1.0, 100.0)
        self.orthoGUIPrjMat = glm.ortho(0, self.displaySize[0], 0, self.displaySize[1], 1.0, 100.0)

        self.view3DMat = glm.mat4()
        self.view2DMat = glm.translate(glm.vec3(0.0, 0.0, 20.0))
        self.view2DMat = glm.inverse(self.view2DMat)

        self.coordAxesViewMat = glm.mat4()

        self.modelMat = glm.mat4()

        self.enableCameraMove = False

        self.objects = []
        self.smallFont = None
        self.font = None
        self.largeFont = None

        self.deltaTime = 0.0
        self.dirty = True

        self.colors = {}

        self.programInfo = False
        self.numProgramInfoElement = 7

        self.specificProgramInfo = True
        self.specificProgramArgs = []

        self.controlFPS = False
        self.FPS = 30
        self.oneFrameTime = 1.0 / self.FPS
        self.deltaTime = 0.0
        self.elapsedTime = 0.0        
        self.enableRender = True

        self.pause = False
        self.debug = False
        self.debugMat = glm.mat4()

        self.numVertexComponents = 7
        self.numDrawingStuff = 2

        self.drawingStuffVAO = None
        self.drawingStuffVBO = None
        self.drawingStuffEBO = None        

        self._InitializeDrawingStuff()

        self._InitializeColors()        

    def GetDisplaySize(self):
        return self.displaySize

    def SetDisplaySize(self, width, height):
        self.displaySize[0] = width
        self.displaySize[1] = height
        self.aspect = self.displaySize[0] / self.displaySize[1]

        self.dirty = True   

    def GetCamera(self):
        return self.camera

    def SetCamera(self, camera):
        self.camera = camera

    def GetView3D(self):
        return self.view3D

    def SetView3D(self, view3D):
        self.view3D = view3D

    def GetEnableCameraMove(self):
        return self.enableCameraMove

    def SetEnableCameraMove(self, enableCameraMove):
        self.enableCameraMove = enableCameraMove

    def GetPerspectivePrjMat(self):
        return self.perspectivePrjMat

    def GetOrthoPrjMat(self):
        return self.orthoGUIPrjMat

    def GetView3DMat(self):
        self.view3DMat = self.camera.GetViewMat()
        return self.view3DMat

    def GetView2DMat(self):
        return self.view2DMat

    def GetPause(self):
        return self.pause    

    def GetColor(self, key, index):
        completedKey = key + str(index)
        return self.colors[completedKey]

    def GetShader(self):
        return self.shader

    def GetScreenPos(self):
        return self.screenPos

    def GetScreenSize(self):
        return self.screenSize

    def SetDirty(self, value):
        self.dirty = value

    def SetCameraPos(self):
        if gInputManager.GetKeyState(glfw.KEY_W) == True:
            self.camera.ProcessKeyboard('FORWARD', 0.05)
            self.dirty = True
        if gInputManager.GetKeyState(glfw.KEY_S) == True:
            self.camera.ProcessKeyboard('BACKWARD', 0.05)
            self.dirty = True
        if gInputManager.GetKeyState(glfw.KEY_A) == True:
            self.camera.ProcessKeyboard('LEFT', 0.05)
            self.dirty = True
        if gInputManager.GetKeyState(glfw.KEY_D) == True:
            self.camera.ProcessKeyboard('RIGHT', 0.05)
            self.dirty = True 
        if gInputManager.GetKeyState(glfw.KEY_E) == True:
            self.camera.ProcessKeyboard('UPWARD', 0.05)
            self.dirty = True
        if gInputManager.GetKeyState(glfw.KEY_Q) == True:
            self.camera.ProcessKeyboard('DOWNWARD', 0.05)
            self.dirty = True 

    def SailCamera(self):
        if self.sailingCamera[0] == True:
            self.camera.ProcessKeyboard('FORWARD', 1.0)
            self.dirty = True
        if self.sailingCamera[1] == True:
            self.camera.ProcessKeyboard('BACKWARD', 1.0)
            self.dirty = True

    def SetSpecificProgramArgs(self, index, subIndex, value):        
        argsList = list(self.specificProgramArgs[index])

        argsList[subIndex] = value     

        self.specificProgramArgs[index] = tuple(argsList)

    def InitializeOpenGL(self, shader):        
        self.shader = shader

        color = self.GetColor('DefaultColor_', 1)
        glClearColor(color[0], color[1], color[2], 1.0)

        glEnable(GL_DEPTH_TEST)

        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)

        self.drawingStuffVAO = glGenVertexArrays(self.numDrawingStuff)
        self.drawingStuffVBO = glGenBuffers(self.numDrawingStuff)
        self.drawingStuffEBO = glGenBuffers(self.numDrawingStuff)

        for i in range(self.numDrawingStuff):
            glBindVertexArray(self.drawingStuffVAO[i])

            glBindBuffer(GL_ARRAY_BUFFER, self.drawingStuffVBO[i])
            glBufferData(GL_ARRAY_BUFFER, self.drawingStuffVerticesList[i].nbytes, self.drawingStuffVerticesList[i], GL_STATIC_DRAW)

            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.drawingStuffEBO[i])
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.drawingStuffIndicesList[i].nbytes, self.drawingStuffIndicesList[i], GL_STATIC_DRAW)

            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, self.drawingStuffVerticesList[i].itemsize * self.numVertexComponents, ctypes.c_void_p(0))

            glEnableVertexAttribArray(1)
            glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, self.drawingStuffVerticesList[i].itemsize * self.numVertexComponents, ctypes.c_void_p(self.drawingStuffVerticesList[i].itemsize * 3))

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)        

        #self.debugMat = glGetFloatv(GL_MODELVIEW_MATRIX)
        #cullFaceMode =  glGetIntegerv(GL_CULL_FACE_MODE)

    def MakeFont(self, fontPath = None):
        if fontPath == None:
            self.smallFont = Font('../../Resource/Font/comic.ttf', 10)
            self.font = Font('../../Resource/Font/comic.ttf', 14)
            self.largeFont = Font('../../Resource/Font/comic.ttf', 21)            

            self.smallFont.MakeFontTextureWithGenList()
            self.font.MakeFontTextureWithGenList()
            self.largeFont.MakeFontTextureWithGenList()

    def AddObject(self, object):
        self.objects.append(object)        
        
    def AddSpecificProgramArgs(self, *args):
        self.specificProgramArgs.append(args)

    def ClearSpecificProgramArgs(self):
        self.specificProgramArgs.clear()

    def UpdateAboutKeyInput(self):
        numObjects = len(self.objects)

        if gInputManager.GetKeyState(glfw.KEY_SPACE) == True:
            for i in range(numObjects):
                self.objects[i].UpdateAboutKeyInput(glfw.KEY_SPACE)
            gInputManager.SetKeyState(glfw.KEY_SPACE, False)    

        elif gInputManager.GetKeyState(glfw.KEY_1) == True:
            self.sailingCamera[0] = not self.sailingCamera[0]
            gInputManager.SetKeyState(glfw.KEY_1, False)        
        elif gInputManager.GetKeyState(glfw.KEY_2) == True:
            self.sailingCamera[1] = not self.sailingCamera[1]
            gInputManager.SetKeyState(glfw.KEY_2, False)
        elif gInputManager.GetKeyState(glfw.KEY_3) == True:
            for i in range(numObjects):
                self.objects[i].UpdateAboutKeyInput(glfw.KEY_3)
            gInputManager.SetKeyState(glfw.KEY_3, False)
        elif gInputManager.GetKeyState(glfw.KEY_4) == True:
            for i in range(numObjects):
                self.objects[i].UpdateAboutKeyInput(glfw.KEY_4)
            gInputManager.SetKeyState(glfw.KEY_4, False)

        elif gInputManager.GetKeyState(glfw.KEY_B) == True:
            self.debug = not self.debug
            gInputManager.SetKeyState(glfw.KEY_B, False)        
        elif gInputManager.GetKeyState(glfw.KEY_F) == True:
            self.specificProgramInfo = not self.specificProgramInfo
            gInputManager.SetKeyState(glfw.KEY_F, False)        
        elif gInputManager.GetKeyState(glfw.KEY_I) == True:
            self.programInfo = not self.programInfo                
            gInputManager.SetKeyState(glfw.KEY_I, False)
        elif gInputManager.GetKeyState(glfw.KEY_P) == True:
            self.pause = not self.pause
            gInputManager.SetMouseEntered(False)
            gInputManager.SetKeyState(glfw.KEY_P, False)
        elif gInputManager.GetKeyState(glfw.KEY_R) == True:
            for i in range(numObjects):
                self.objects[i].Restart()
            gInputManager.SetKeyState(glfw.KEY_R, False)
        elif gInputManager.GetKeyState(glfw.KEY_V) == True:
            self.view3D = not self.view3D
            for i in range(numObjects):
                self.objects[i].Restart()
            gInputManager.SetKeyState(glfw.KEY_V, False)
        elif gInputManager.GetKeyState(glfw.KEY_X) == True:
            self.drawAxes = not self.drawAxes
            gInputManager.SetKeyState(glfw.KEY_X, False)

        if gInputManager.GetKeyState(glfw.KEY_LEFT) == True:
            for i in range(numObjects):
                self.objects[i].UpdateAboutKeyInput(glfw.KEY_LEFT)
        if gInputManager.GetKeyState(glfw.KEY_RIGHT) == True:
            for i in range(numObjects):
                self.objects[i].UpdateAboutKeyInput(glfw.KEY_RIGHT)  
        if gInputManager.GetKeyState(glfw.KEY_UP) == True:            
            for i in range(numObjects):
                self.objects[i].UpdateAboutKeyInput(glfw.KEY_UP)
        if gInputManager.GetKeyState(glfw.KEY_DOWN) == True:
            for i in range(numObjects):
                self.objects[i].UpdateAboutKeyInput(glfw.KEY_DOWN)            

    def UpdateAboutMouseInput(self):
        pass

    def PostUpdate(self, deltaTime):
        if gInputManager.GetKeyState(glfw.KEY_8) == True:
            if self.controlFPS == True:
                self.FPS -= 5
                if self.FPS <= 0:
                    self.FPS = 1

                self.oneFrameTime = 1.0 / self.FPS
                self.elapsedTime = 0.0
                self.enableRender = False

            gInputManager.SetKeyState(glfw.KEY_8, False)

        if gInputManager.GetKeyState(glfw.KEY_9) == True:
            if self.controlFPS == True:
                self.FPS = int(self.FPS / 5) * 5 + 5
                if self.FPS > 100:
                    self.FPS = 100

                self.oneFrameTime = 1.0 / self.FPS
                self.elapsedTime = 0.0
                self.enableRender = False        

            gInputManager.SetKeyState(glfw.KEY_9, False)        

        if gInputManager.GetKeyState(glfw.KEY_0) == True:
            self.controlFPS = not self.controlFPS

            if self.controlFPS == True:
                self.elapsedTime = 0.0        
                self.enableRender = False

            gInputManager.SetKeyState(glfw.KEY_0, False)

        if self.enableRender == True:
            self.elapsedTime = 0.0
            self.enableRender = False

    def Update(self, deltaTime):
        self.deltaTime = deltaTime

        self.shader.Use()

        if self.controlFPS == True:
            self.elapsedTime += deltaTime

            if self.elapsedTime < self.oneFrameTime:                
                return        
        
        self.enableRender = True        

        self.UpdateAboutKeyInput()

        self.UpdateAboutMouseInput()

        if self.view3D == True and self.enableCameraMove:
            self.SetCameraPos()
            self.SailCamera()

        if self.pause == True:
            return

        numObjects = len(self.objects)

        for i in range(numObjects):
            if self.controlFPS == True:
                self.objects[i].Update(self.elapsedTime)
            else:
                self.objects[i].Update(deltaTime)        

        if self.dirty == False:
            return  

        self.view3DMat = self.camera.GetViewMat()
        self.coordAxesViewMat = self.camera.GetViewMat()

        self.deltaTime += deltaTime
        self.dirty = False
        
    def Draw(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glViewport(self.screenPos[0][0], self.screenPos[0][1], self.screenSize[0], self.screenSize[1])

        self._DrawObjects()

        glViewport(0, 0, self.displaySize[0], self.displaySize[1])

        self._DrawGUI()        

    def _InitializeDrawingStuff(self):
        self.screenPos.clear()
        
        screenLbPos = [20, 20]
        screenRtPos = []
        screenRtPos.append(screenLbPos[0] + self.screenSize[0])
        screenRtPos.append(screenLbPos[1] + self.screenSize[1])

        self.screenPos.append(screenLbPos)
        self.screenPos.append(screenRtPos)

        coordAxesVerticesData = [
            0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0,
            1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0,

            0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0,
            0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0,

            0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0,
            0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0
            ]

        coordAxesIndicesData = [
            0, 1,
            2, 3,
            4, 5
            ]

        self.coordAxesVertices = np.array(coordAxesVerticesData, dtype = np.float32)
        self.coordAxesIndices = np.array(coordAxesIndicesData, dtype = np.uint32)

        startPos = [self.screenPos[0][0] + 10, self.screenPos[1][1] - 10]
        interval = [3.0, 5.0, 200.0]
        sideLength = interval[0] * 2 + interval[1] * 2 + interval[2]

        squarePos = []
        squarePos.append(startPos)
        squarePos.append([startPos[0] + sideLength, startPos[1]])
        squarePos.append([startPos[0] + sideLength, startPos[1] - sideLength])
        squarePos.append([startPos[0], startPos[1] - sideLength])

        programInfoAreaVerticesData = [
            squarePos[0][0] + interval[0] + interval[1], squarePos[0][1], 9.0, 1.0, 1.0, 1.0, 1.0,
            squarePos[1][0] - interval[0] - interval[1], squarePos[1][1], 9.0, 1.0, 1.0, 1.0, 1.0,
            squarePos[0][0] + interval[0] + interval[1], squarePos[0][1] - interval[0], 9.0, 1.0, 1.0, 1.0, 1.0,
            squarePos[1][0] - interval[0] - interval[1], squarePos[1][1] - interval[0], 9.0, 1.0, 1.0, 1.0, 1.0,

            squarePos[1][0], squarePos[1][1] - interval[0] - interval[1], 9.0, 0.0, 0.0, 1.0, 0.8,
            squarePos[2][0], squarePos[2][1] + interval[0] + interval[1], 9.0, 0.0, 0.0, 1.0, 0.8,
            squarePos[1][0] - interval[0], squarePos[1][1] - interval[0] - interval[1], 9.0, 0.0, 0.0, 1.0, 0.8,
            squarePos[2][0] - interval[0], squarePos[2][1] + interval[0] + interval[1], 9.0, 0.0, 0.0, 1.0, 0.8,

            squarePos[2][0] - interval[0] - interval[1], squarePos[2][1], 9.0, 0.0, 0.0, 1.0, 0.8,
            squarePos[3][0] + interval[0] + interval[1], squarePos[3][1], 9.0, 0.0, 0.0, 1.0, 0.8,
            squarePos[2][0] - interval[0] - interval[1], squarePos[2][1] + interval[0], 9.0, 0.0, 0.0, 1.0, 0.8,
            squarePos[3][0] + interval[0] + interval[1], squarePos[3][1] + interval[0], 9.0, 0.0, 0.0, 1.0, 0.8,

            squarePos[3][0], squarePos[3][1] + interval[0] + interval[1], 9.0, 0.0, 0.0, 1.0, 0.8,
            squarePos[0][0], squarePos[0][1] - interval[0] - interval[1], 9.0, 0.0, 0.0, 1.0, 0.8,
            squarePos[3][0] + interval[0], squarePos[3][1] + interval[0] + interval[1], 9.0, 0.0, 0.0, 1.0, 0.8,
            squarePos[0][0] + interval[0], squarePos[0][1] - interval[0] - interval[1], 9.0, 0.0, 0.0, 1.0, 0.8            
            ]
        
        programInfoAreaIndicesData = [
            0, 1,
            2, 3,

            4, 5,
            6, 7,

            8, 9,
            10, 11,

            12, 13,
            14, 15
            ]

        self.programInfoAreaVertices = np.array(programInfoAreaVerticesData, dtype = np.float32)
        self.programInfoAreaIndices = np.array(programInfoAreaIndicesData, dtype = np.uint32)

        self.drawingStuffVerticesList.append(self.coordAxesVertices)
        self.drawingStuffVerticesList.append(self.programInfoAreaVertices)

        self.drawingStuffIndicesList.append(self.coordAxesIndices)
        self.drawingStuffIndicesList.append(self.programInfoAreaIndices)        

    def _InitializeColors(self):
        self.colors['DefaultColor_0'] = [1.0, 1.0, 1.0]
        self.colors['DefaultColor_1'] = [0.0, 0.0, 0.0]
        self.colors['DefaultColor_2'] = [1.0, 0.0, 0.0]
        self.colors['DefaultColor_3'] = [0.0, 1.0, 0.0]
        self.colors['DefaultColor_4'] = [0.0, 0.0, 1.0]
        self.colors['DefaultColor_5'] = [0.8, 0.3, 0.5]
        self.colors['DefaultColor_6'] = [0.3, 0.8, 0.5]
        self.colors['DefaultColor_7'] = [0.2, 0.3, 0.98]

        self.colors['ObjectColor_0'] = [1.0, 0.0, 0.0]
        self.colors['ObjectColor_1'] = [0.0, 0.76, 0.0]
        self.colors['ObjectColor_2'] = [0.15, 0.18, 0.85]
        self.colors['ObjectColor_3'] = [0.9, 0.73, 0.0]
        self.colors['ObjectColor_4'] = [0.95, 0.0, 0.89]
        self.colors['ObjectColor_5'] = [0.0, 0.9, 0.91]
        self.colors['ObjectColor_6'] = [1.0, 0.56, 0.0]

    def _DrawCoordAxes(self):
        if self.view3D == False or self.drawAxes == False:
            return

        glViewport(530, 530, 40, 40)

        self.coordAxesViewMat[3].x = 0.0
        self.coordAxesViewMat[3].y = 0.0
        self.coordAxesViewMat[3].z = -2.0

        self.shader.SetMat4('prjMat', self.perspectivePrjMat)
        self.shader.SetMat4('viewMat', self.coordAxesViewMat)

        glLineWidth(2.0)

        glBindVertexArray(self.drawingStuffVAO[0])
        glDrawElements(GL_LINES, len(self.drawingStuffIndicesList[0]), GL_UNSIGNED_INT, None)

        glBindVertexArray(0)

        glViewport(0, 0, self.displaySize[0], self.displaySize[1])

    def _DrawObjects(self):
        numObjects = len(self.objects)

        if self.view3D == True:
            prjMat = self.perspectivePrjMat
            viewMat = self.view3DMat            
        else:
            prjMat = self.orthoPrjMat
            viewMat = self.view2DMat

        self.shader.SetMat4('prjMat', prjMat)
        self.shader.SetMat4('viewMat', viewMat)

        for i in range(numObjects):
            self.objects[i].Draw()

    def _DrawGUI(self):
        glPushAttrib(GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT | GL_LINE_BIT)

        glEnable(GL_BLEND)

        glDisable(GL_DEPTH_TEST)

        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.shader.SetMat4('modelMat', self.modelMat)

        self._DrawCoordAxes()

        self._DrawProgramInfoArea()        

        glUseProgram(0)

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()

        glOrtho(0, self.displaySize[0], 0, self.displaySize[1], -10.0, 10.0)        

        glMatrixMode(GL_MODELVIEW)

        glEnable(GL_TEXTURE_2D)

        glDisable(GL_CULL_FACE)

        self._DrawProgramInfo()

        self._DrawSpecificProgramInfo()

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()

        glPopAttrib()
       
    def _DrawProgramInfoArea(self):
        if self.programInfo == False:
            return

        self.shader.SetMat4('prjMat', self.orthoGUIPrjMat)
        self.shader.SetMat4('viewMat', self.view2DMat)       
        
        glLineWidth(1.0)
                
        glBindVertexArray(self.drawingStuffVAO[1])
        glDrawElements(GL_LINES, len(self.drawingStuffIndicesList[1]), GL_UNSIGNED_INT, None)        

        glBindVertexArray(0)        
       
    def _DrawProgramInfo(self):
        if self.programInfo == False:
            return

        glPushMatrix()
        glLoadIdentity()

        font = self.smallFont
        
        texId = font.GetTexId()

        glBindTexture(GL_TEXTURE_2D, texId)
        
        color = self.GetColor('DefaultColor_', 6)
        glColor(color[0], color[1], color[2], 1.0)

        infoText = []
        infoTextIndex = 0
        infoFPSText = ". FPS"

        if self.controlFPS == True:
            infoFPSText += ".On(8, 9; 0)"
        else:
            infoFPSText += ".Off(0)"

        infoText.append(infoFPSText + ' : {0: 0.2f}'.format(0.0))
        
        if self.controlFPS == True:
            if self.elapsedTime != 0.0:
                infoText[infoTextIndex] = infoFPSText + " : {0: 0.2f} ({1})".format(1.0 / self.elapsedTime, self.FPS)
                #print('.FPS: {0: 0.2f} ({1})'.format(1.0 / self.elapsedTime, self.FPS))
        else:
            if self.deltaTime != 0.0:
                infoText[infoTextIndex] = infoFPSText + " : {0: 0.2f}".format(1.0 / self.deltaTime)
                #print('.FPS: {0: 0.2f}'.format(1.0 / deltaTime))            

        infoText.append('. ViewMode(V) : ')
        infoTextIndex += 1

        if self.view3D == True:
            infoText[infoTextIndex] += "3D"
        else:
            infoText[infoTextIndex] += "2D"

        infoText.append('.    DrawAxes(X) : ')
        infoTextIndex += 1

        if self.drawAxes == True:
            infoText[infoTextIndex] += "On"
        else:
            infoText[infoTextIndex] += "Off"        

        infoText.append('. Pause(P) : ')
        infoTextIndex += 1
        
        if self.pause == True:
            infoText[infoTextIndex] += "On"
        else:
            infoText[infoTextIndex] += "Off"

        infoText.append('. CameraMove(M.R) : ')
        infoTextIndex += 1
        
        if self.enableCameraMove == True:
            infoText[infoTextIndex] += "On"
        else:
            infoText[infoTextIndex] += "Off"

        infoText.append('.    SailingDir(1, 2) : ')
        infoTextIndex += 1

        if self.sailingCamera[0] == True:
            infoText[infoTextIndex] += "F"
        if self.sailingCamera[1] == True:
            infoText[infoTextIndex] += "B"        

        infoText.append('. Debug(B) : ')
        infoTextIndex += 1
        
        if self.debug == True:
            infoText[infoTextIndex] += "On"
        else:
            infoText[infoTextIndex] += "Off"

        textPosX = self.screenPos[0][0] + 20
        textPosY = self.screenPos[1][1] - 25

        for i in range(self.numProgramInfoElement):
            glTranslate(textPosX, textPosY, 0.0)

            glListBase(font.GetListOffset())
            glCallLists([ord(c) for c in infoText[i]])        

            glPopMatrix()
            glPushMatrix()
            glLoadIdentity()

            if i == self.numProgramInfoElement - 2:                
                textPosY -= 100.0
            else:
                textPosY -= 15.0

        glPopMatrix()

    def _DrawSpecificProgramInfo(self):
        if self.specificProgramInfo == False:
            return
        
        glPushMatrix()
        glLoadIdentity()        

        color = []
        textPos = [0.0, 0.0]
        textIntervalY = 0.0
        font = None
        infoText = []
        numInfoTexts = 0

        for i in range(len(self.specificProgramArgs)):
            args = self.specificProgramArgs[i]

            color = args[0]
            glColor(color[0], color[1], color[2], 1.0)

            textPos[0] = args[1][0]
            textPos[1] = args[1][1]
            textIntervalY = args[2]
            numInfoTexts = args[3]

            infoText = args[5 : ]

            if 'Large' == args[4]:
                font = self.largeFont
            elif 'Medium' == args[4]:
                font = self.font

            texId = font.GetTexId()
            glBindTexture(GL_TEXTURE_2D, texId)

            for i in range(numInfoTexts):
                glTranslate(textPos[0], textPos[1], 0.0)               

                glListBase(font.GetListOffset())
                glCallLists([ord(c) for c in infoText[i]])        

                glPopMatrix()
                glPushMatrix()
                glLoadIdentity()
            
                textPos[1] -= textIntervalY        

        glPopMatrix()

class InputManager:
    def __init__(self):
        self.mouseEntered = False

        self.mouseButtonClick = [False, False, False]
        self.lastMousePos = [-1, -1]
        self.lastMousePosOnClick = [-1, -1]

        self.keys = {}

    def GetMouseEntered(self):
        return self.mouseEntered

    def SetMouseEntered(self, value):
        self.mouseEntered = value

    def GetMouseButtonClick(self, key):
        return self.mouseButtonClick[key]

    def SetMouseButtonClick(self, key, value):
        self.mouseButtonClick[key] = value

    def GetLastMousePos(self):
        return self.lastMousePos

    def SetLastMousePos(self, value):
        self.lastMousePos = value    

    def GetLastMousePosOnClick(self):
        return self.lastMousePosOnClick

    def SetLastMousePosOnClick(self, value):
        self.lastMousePosOnClick = value

    def GetKeyState(self, key):        
        if key in self.keys.keys():            
            return self.keys[key]

    def SetKeyState(self, key, value):
        self.keys[key] = value

class Camera:
    def __init__(self, cameraPos = None):
        if cameraPos == None:
            self.cameraPos = glm.vec3(0.0, 0.0, 10.0)
        else:
            self.cameraPos = cameraPos
            
        self.cameraFront = glm.vec3(0.0, 0.0, -1.0)
        self.cameraUp = glm.vec3(0.0, 1.0, 0.0)
        self.cameraRight = glm.vec3(1.0, 0.0, 0.0)
        self.cameraWorldUp = glm.vec3(0.0, 1.0, 0.0)

        self.pitch = 0.0
        self.yaw = 180.0

        self.mouseSensitivity = 0.1

        self.UpdateCameraVectors()

    def GetPos(self):
        return self.cameraPos

    def SetPos(self, cameraPos):
        self.cameraPos = cameraPos

    def GetViewMat(self):
        return glm.lookAt(self.cameraPos, self.cameraPos + self.cameraFront, self.cameraUp)    

    def ProcessMouseMovement(self, xOffset, yOffset, constrainPitch = True):
        xOffset *= self.mouseSensitivity
        yOffset *= self.mouseSensitivity

        self.yaw += xOffset
        self.pitch += yOffset

        if constrainPitch == True:
            if self.pitch > 89.0:
                self.pitch = 89.0
            elif self.pitch < -89.0:
                self.pitch = -89.0

        self.UpdateCameraVectors()

    def ProcessKeyboard(self, direction, velocity):
        if direction == "FORWARD":
            self.cameraPos += self.cameraFront * velocity
        elif direction == "BACKWARD":
            self.cameraPos -= self.cameraFront * velocity
        elif direction == "LEFT":
            self.cameraPos += self.cameraRight * velocity
        elif direction == "RIGHT":
            self.cameraPos -= self.cameraRight * velocity
        elif direction == "UPWARD":
            self.cameraPos += self.cameraUp * velocity
        elif direction == "DOWNWARD":
            self.cameraPos -= self.cameraUp * velocity

    def UpdateCameraVectors(self):
        self.cameraFront.x = math.sin(glm.radians(self.yaw)) * math.cos(glm.radians(self.pitch))
        self.cameraFront.y = math.sin(glm.radians(self.pitch))
        self.cameraFront.z = math.cos(glm.radians(self.yaw)) * math.cos(glm.radians(self.pitch))

        self.cameraFront = glm.normalize(self.cameraFront)

        self.cameraRight = glm.normalize(glm.cross(self.cameraWorldUp, self.cameraFront))
        self.cameraUp = glm.normalize(glm.cross(self.cameraFront, self.cameraRight))

class Shader:
    def __init__(self, vsCode, fsCode):
        self.program = None

        self.program = compileProgram(compileShader(vsCode, GL_VERTEX_SHADER), compileShader(fsCode, GL_FRAGMENT_SHADER))

    def Use(self):
        glUseProgram(self.program)

    def SetBool(self, name, value):
        loc = glGetUniformLocation(self.program, name)
        
        glUniform1i(loc, value)

    def SetVec2(self, name, x, y):
        loc = glGetUniformLocation(self.program, name)
        
        glUniform2f(loc, x, y)

    def SetVec3(self, name, x, y, z):
        loc = glGetUniformLocation(self.program, name)
        
        glUniform3f(loc, x, y, z)

    def SetVec4(self, name, x, y, z, w):
        loc = glGetUniformLocation(self.program, name)
        
        glUniform4f(loc, x, y, z, w)

    def SetMat4(self, name, value):
        loc = glGetUniformLocation(self.program, name)

        value = np.array(value, dtype = np.float32)
        glUniformMatrix4fv(loc, 1, GL_TRUE, value)

class Font:
    def __init__(self, fontPath, size):
        self.face = ft.Face(fontPath)
        self.face.set_char_size(size << 6)

        self.charsSize = (6, 16)
        self.charsAdvanceX = []

        self.maxCharHeight = 0
        self.charStartOffset = 32
        self.listOffset = -1
        self.texId = -1

        numChars = self.charsSize[0] * self.charsSize[1]

        self.charsAdvanceX = [0 for i in range(numChars)]

        advanceX, ascender, descender = 0, 0, 0
        charEndIndex = self.charStartOffset + numChars

        for c in range(self.charStartOffset, charEndIndex):
            self.face.load_char(chr(c), ft.FT_LOAD_RENDER | ft.FT_LOAD_FORCE_AUTOHINT)

            self.charsAdvanceX[c - self.charStartOffset] = self.face.glyph.advance.x >> 6

            advanceX = max(advanceX, self.face.glyph.advance.x >> 6)
            ascender = max(ascender, self.face.glyph.metrics.horiBearingY >> 6)
            descender = max(descender, (self.face.glyph.metrics.height >> 6) - (self.face.glyph.metrics.horiBearingY >> 6))

        self.maxCharHeight = ascender + descender
        maxTotalAdvanceX = advanceX * self.charsSize[1]
        maxTotalHeight = self.maxCharHeight * self.charsSize[0]

        exponent = 0
        bitmapDataSize = [0, 0]

        while maxTotalAdvanceX > math.pow(2, exponent):
            exponent += 1
        bitmapDataSize[1] = int(math.pow(2, exponent))

        exponent = 0

        while maxTotalHeight > math.pow(2, exponent):
            exponent += 1
        bitmapDataSize[0] = int(math.pow(2, exponent))

        self.bitmapData = np.zeros((bitmapDataSize[0], bitmapDataSize[1]), dtype = np.ubyte)

        x, y, charIndex = 0, 0, 0

        for r in range(self.charsSize[0]):
            for c in range(self.charsSize[1]):
                self.face.load_char(chr(self.charStartOffset + r * self.charsSize[1] + c), ft.FT_LOAD_RENDER | ft.FT_LOAD_FORCE_AUTOHINT)

                charIndex = r * self.charsSize[1] + c

                bitmap = self.face.glyph.bitmap
                x += self.face.glyph.bitmap_left
                y = r * self.maxCharHeight + ascender - self.face.glyph.bitmap_top

                self.bitmapData[y : y + bitmap.rows, x : x + bitmap.width].flat = bitmap.buffer

                x += self.charsAdvanceX[charIndex] - self.face.glyph.bitmap_left

            x = 0

    def GetTexId(self):
        return self.texId

    def GetListOffset(self):
        return self.listOffset

    def MakeFontTextureWithGenList(self):
        self.texId = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, self.texId)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER)

        self.bitmapData = np.flipud(self.bitmapData)

        glTexImage2D(GL_TEXTURE_2D, 0, GL_ALPHA, self.bitmapData.shape[1], self.bitmapData.shape[0], 0,
                     GL_ALPHA, GL_UNSIGNED_BYTE, self.bitmapData)

        dx = 0.0
        dy = self.maxCharHeight / float(self.bitmapData.shape[0])

        listStartIndex = glGenLists(self.charsSize[0] * self.charsSize[1])
        self.listOffset = listStartIndex - self.charStartOffset

        for r in range(self.charsSize[0]):
            for c in range(self.charsSize[1]):
                glNewList(listStartIndex + r * self.charsSize[1] + c, GL_COMPILE)

                charIndex = r * self.charsSize[1] + c

                advanceX = self.charsAdvanceX[charIndex]
                dAdvanceX = advanceX / float(self.bitmapData.shape[1])

                glBegin(GL_QUADS)
                glTexCoord2f(dx, 1.0 - r * dy), glVertex3f(0.0, 0.0, 0.0)
                glTexCoord2f(dx + dAdvanceX, 1.0 - r * dy), glVertex3f(advanceX, 0.0, 0.0)
                glTexCoord2f(dx + dAdvanceX, 1.0 - (r + 1) * dy), glVertex3f(advanceX, -self.maxCharHeight, 0.0)
                glTexCoord2f(dx, 1.0 - (r + 1) * dy), glVertex3f(0.0, -self.maxCharHeight, 0.0)
                glEnd()

                glTranslate(advanceX, 0.0, 0.0)

                glEndList()

                dx += dAdvanceX

            glTranslatef(0.0, -self.maxCharHeight, 0.0)
            dx = 0.0

class Model:
    def __init__(self, modelPath):
        self.vertices = []
        self.normals = []
        self.indices = []

        self.normalLineVertices = []
        self.normalLineIndices = []

        self.normalLineScale = 0.001

        self.numVertices = 0
        self.numNoUseVertices = 0
        self.numFaces = 0

        self._Initialize(modelPath)

    def GetVertices(self):
        return self.vertices

    def GetIndices(self):
        return self.indices

    def GetNormalLineVertices(self):
        return self.normalLineVertices

    def GetNormalLineIndices(self):
        return self.normalLineIndices

    def GetNumVertices(self):
        return self.numVertices

    def _Initialize(self, modelPath):
        with open(modelPath, mode = 'r') as fin:
            for line in fin:
                cl = line.split()

                if len(cl) == 0:
                    continue
                elif cl[0] in ['#']:
                    continue
                elif cl[0] == 'v':
                    for v in cl[1 : len(cl)]:
                        self.vertices.append(float(v))
                elif cl[0] == 'f':
                    for i in cl[1 : len(cl)]:
                        self.indices.append(int(i) - 1)

        self.numVertices = int(len(self.vertices) / 3)
        self.numFaces = int(len(self.indices) / 3)

        self.normals = np.zeros(len(self.vertices), dtype = np.float32)

        for i in range(self.numFaces):
            vertexAIndex = self.indices[i * 3 + 0]
            vertexBIndex = self.indices[i * 3 + 1]
            vertexCIndex = self.indices[i * 3 + 2]

            vecA = glm.vec3(self.vertices[vertexAIndex * 3 + 0], self.vertices[vertexAIndex * 3 + 1], self.vertices[vertexAIndex * 3 + 2])
            vecB = glm.vec3(self.vertices[vertexBIndex * 3 + 0], self.vertices[vertexBIndex * 3 + 1], self.vertices[vertexBIndex * 3 + 2])
            vecC = glm.vec3(self.vertices[vertexCIndex * 3 + 0], self.vertices[vertexCIndex * 3 + 1], self.vertices[vertexCIndex * 3 + 2])

            vecAB = vecB - vecA
            vecAC = vecC - vecA

            faceNormal = glm.normalize(glm.cross(vecAB, vecAC))

            self.normals[vertexAIndex * 3 + 0] += faceNormal.x
            self.normals[vertexAIndex * 3 + 1] += faceNormal.y
            self.normals[vertexAIndex * 3 + 2] += faceNormal.z

            self.normals[vertexBIndex * 3 + 0] += faceNormal.x
            self.normals[vertexBIndex * 3 + 1] += faceNormal.y
            self.normals[vertexCIndex * 3 + 2] += faceNormal.z

            self.normals[vertexCIndex * 3 + 0] += faceNormal.x
            self.normals[vertexCIndex * 3 + 1] += faceNormal.y
            self.normals[vertexCIndex * 3 + 2] += faceNormal.z

        useVertices = np.zeros(self.numVertices, dtype = np.bool8)

        for i in range(len(self.indices)):
            index = self.indices[i]
            useVertices[index] = True

        for i in range(self.numVertices):
            if useVertices[i] == True:
                vertexNormal = glm.vec3(self.normals[i * 3 + 0], self.normals[i * 3 + 1], self.normals[i * 3 + 2])
                vertexNormal = glm.normalize(vertexNormal)

                self.normals[i * 3 + 0] = vertexNormal.x
                self.normals[i * 3 + 1] = vertexNormal.y
                self.normals[i * 3 + 2] = vertexNormal.z

        for i in range(self.numVertices):
            if useVertices[i] == False:
                self.vertices[i * 3 + 0] = 10000.0
                self.vertices[i * 3 + 1] = 0.0
                self.vertices[i * 3 + 2] = 0.0

                self.normals[i * 3 + 0] = 10000.0
                self.normals[i * 3 + 1] = 0.0
                self.normals[i * 3 + 2] = 0.0

                self.numNoUseVertices += 1

        normalLineVerticesData = []
        normalLineIndicesData = []

        for i in range(self.numVertices):
            normalLineVerticesData.append(self.vertices[i * 3 + 0])
            normalLineVerticesData.append(self.vertices[i * 3 + 1])
            normalLineVerticesData.append(self.vertices[i * 3 + 2])

            normalLineVerticesData.append(self.vertices[i * 3 + 0] + self.normals[i * 3 + 0] * self.normalLineScale)
            normalLineVerticesData.append(self.vertices[i * 3 + 1] + self.normals[i * 3 + 1] * self.normalLineScale)
            normalLineVerticesData.append(self.vertices[i * 3 + 2] + self.normals[i * 3 + 2] * self.normalLineScale)

        for i in range(self.numVertices):
            normalLineIndicesData.append(i * 2 + 0)
            normalLineIndicesData.append(i * 2 + 1)

        self.normalLineVertices = np.array(normalLineVerticesData, dtype = np.float32)
        self.normalLineIndices = np.array(normalLineIndicesData, dtype = np.uint32)

gSceneManager = SceneManager(True)
gInputManager = InputManager()


class TestProgram:
    def __init__(self, programName, imguiNewFont):
        self.programName = programName       

        self.drawingStuffVerticesList = []        
        self.drawingStuffIndicesList = []

        self.models = []

        self.objectsVertices = []
        self.objectsIndices = []

        self.objectsNormalLineVertices = []
        self.objectsNormalLineIndices = []

        self.GUIStuffVerticesList = []
        self.GUIStuffIndicesList = []

        self.backgroundVertices = []
        self.backgroundIndices = []
        
        self.backgroundLineVertices = []
        self.backgroundLineIndices = []

        self.imguiPos = []
        self.imguiSize = []

        self.imguiNewFont = imguiNewFont

        self.imguiRenderElements = {'Vertex' : False, 'Edge' : True, 'Face' : True, 'Normal' : False}
        self.imguiRenderViewTypes = {'BackFace' : True, 'Lighting' : False}
        self.imguiTest = {'factor' : 0.0, 'units' : 0.0}

        self.rotDegree = 0.0
        self.rotSpeed = 20.0
        
        self.modelMat = glm.mat4()
        self.GUIModelMat = glm.mat4()

        self.objectType = 5
        
        self.numVertexComponentsInModel = 3
        self.numVertexComponents = 7
        self.numVertexComponentsWithTexCoord = 9        
        self.numDrawingStuff = 2        
        self.numGUIStuff = 2

        self.drawingStuffVAO = glGenVertexArrays(self.numDrawingStuff)
        self.drawingStuffVBO = glGenBuffers(self.numDrawingStuff)
        self.drawingStuffEBO = glGenBuffers(self.numDrawingStuff)

        self.GUIVAO = glGenVertexArrays(self.numGUIStuff)
        self.GUIVBO = glGenBuffers(self.numGUIStuff)
        self.GUIEBO = glGenBuffers(self.numGUIStuff)

        self._Initialize()        

    def Restart(self):
        self._Initialize()        

    def UpdateAboutKeyInput(self, key, value = True):
        pass

    def UpdateAboutMouseInput(self, button, pos):
        pass            

    def Update(self, deltaTime):
        if gSceneManager.GetView3D() != True:
            return

        self.rotDegree += deltaTime * self.rotSpeed

        if self.rotDegree > 360.0:
            self.rotDegree -= 360.0

        self._UpdateNewFrameImgui(deltaTime)

    def Draw(self):
        if gSceneManager.GetView3D() != True:
            return       

        displaySize = gSceneManager.GetDisplaySize()
        screenPos = gSceneManager.GetScreenPos()
        screenSize = gSceneManager.GetScreenSize()

        shader = gSceneManager.GetShader()
        
        shader.SetMat4('prjMat', gSceneManager.GetPerspectivePrjMat())
        shader.SetMat4('viewMat', gSceneManager.GetView3DMat())

        glViewport(screenPos[0][0], screenPos[0][1], screenSize[0], screenSize[1])

        self._DrawDrawingStuff()        
            
        glViewport(0, 0, displaySize[0], displaySize[1])
        
        shader.SetMat4('prjMat', gSceneManager.GetOrthoPrjMat())
        shader.SetMat4('viewMat', gSceneManager.GetView2DMat())

        self._DrawGUI()

    def _Initialize(self):
        gSceneManager.SetView3D(True)

        self.rotDegree = 0.0
        self.drawingModelMat = glm.mat4()        
        
        self._InitializeDrawingStuff()
        
        self._InitializeGUIStuff()

    def _InitializeCube(self):
        cubeVerticesData = [            
            # Front
            -0.5, -0.5, 0.5, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0,
            0.5, -0.5, 0.5, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0,
            0.5, 0.5, 0.5, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0,
            -0.5, 0.5, 0.5, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0,

            # Back
            0.5, -0.5, -0.5, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0,
            -0.5, -0.5, -0.5, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0,
            -0.5, 0.5, -0.5, 0.0, 1.0, 0.0, 1.0, 1.0, 1.0,
            0.5, 0.5, -0.5, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0,

            # Left
            -0.5, -0.5, -0.5, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0,
            -0.5, -0.5, 0.5, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0,
            -0.5, 0.5, 0.5, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0,
            -0.5, 0.5, -0.5, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0,

            # Right
            0.5, -0.5, 0.5, 1.0, 1.0, 0.0, 1.0, 0.0, 0.0,
            0.5, -0.5, -0.5, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0,
            0.5, 0.5, -0.5, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0,
            0.5, 0.5, 0.5, 1.0, 1.0, 0.0, 1.0, 0.0, 1.0,

            # Top
            -0.5, 0.5, 0.5, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0,
            0.5, 0.5, 0.5, 0.0, 1.0, 1.0, 1.0, 1.0, 0.0,
            0.5, 0.5, -0.5, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0,
            -0.5, 0.5, -0.5, 0.0, 1.0, 1.0, 1.0, 0.0, 1.0,

            # Bottom
            -0.5, -0.5, -0.5, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0,
            0.5, -0.5, -0.5, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0,
            0.5, -0.5, 0.5, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0,
            -0.5, -0.5, 0.5, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0
            ]

        cubeIndicesData = [
            0, 1, 2, 2, 3, 0,
            4, 5, 6, 6, 7, 4,
            8, 9, 10, 10, 11, 8,
            12, 13, 14, 14, 15, 12,
            16, 17, 18, 18, 19, 16,
            20, 21, 22, 22, 23, 20
            ]

        return cubeVerticesData, cubeIndicesData

    def _InitializeOBJ(self):
        self.models.append(Model('../../Resource/Object/stanford-bunny.obj'))

        return self.models[0].GetVertices(), self.models[0].GetIndices(), self.models[0].GetNormalLineVertices(), self.models[0].GetNormalLineIndices()

    def _InitializeDrawingStuff(self):
        numVertexComponts = 0

        if self.objectType == 0:            
            cubeVerticesData, cubeIndicesData = self._InitializeCube()

            self.objectsVertices = np.array(cubeVerticesData, dtype = np.float32)
            self.objectsIndices = np.array(cubeIndicesData, dtype = np.uint32)

            numVertexComponts = self.numVertexComponentsWithTexCoord

        elif self.objectType == 5:
            modelVerticesData, modelIndicesData, modelNormalLineVerticesData, modelNormalLineIndicesData = self._InitializeOBJ()

            self.objectsVertices = np.array(modelVerticesData, dtype = np.float32)
            self.objectsIndices = np.array(modelIndicesData, dtype = np.uint32)

            self.objectNormalLineVertices = np.array(modelNormalLineVerticesData, dtype = np.float32)
            self.objectNormalLineIndices = np.array(modelNormalLineIndicesData, dtype = np.uint32)

            numVertexComponts = self.numVertexComponentsInModel
        
        self.drawingStuffVerticesList.clear()
        self.drawingStuffIndicesList.clear()

        self.drawingStuffVerticesList.append(self.objectsVertices)
        self.drawingStuffVerticesList.append(self.objectNormalLineVertices)
        
        self.drawingStuffIndicesList.append(self.objectsIndices)
        self.drawingStuffIndicesList.append(self.objectNormalLineIndices)

        for i in range(self.numDrawingStuff):
            glBindVertexArray(self.drawingStuffVAO[i])

            glBindBuffer(GL_ARRAY_BUFFER, self.drawingStuffVBO[i])
            glBufferData(GL_ARRAY_BUFFER, self.drawingStuffVerticesList[i].nbytes, self.drawingStuffVerticesList[i], GL_STATIC_DRAW)

            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.drawingStuffEBO[i])
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.drawingStuffIndicesList[i].nbytes, self.drawingStuffIndicesList[i], GL_STATIC_DRAW)

            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, self.drawingStuffVerticesList[i].itemsize * numVertexComponts, ctypes.c_void_p(0))

            if self.objectType != 5:
                glEnableVertexAttribArray(1)
                glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, self.drawingStuffVerticesList[i].itemsize * numVertexComponts, ctypes.c_void_p(self.drawingStuffVerticesList[i].itemsize * 3))

            if self.objectType != 5:
                glEnableVertexAttribArray(2)
                glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, self.drawingStuffVerticesList[i].itemsize * numVertexComponts, ctypes.c_void_p(self.drawingStuffVerticesList[i].itemsize * 7))

        glBindBuffer(GL_ARRAY_BUFFER, 0);
        glBindVertexArray(0)    

    def _InitializeGUIStuff(self):
        gSceneManager.ClearSpecificProgramArgs()

        displaySize = gSceneManager.GetDisplaySize()
        screenPos = gSceneManager.GetScreenPos()

        imguiInterval = 5

        self.imguiPos.append(screenPos[1][0] + imguiInterval)
        self.imguiPos.append(displaySize[1] - screenPos[1][1] + imguiInterval)

        self.imguiSize.append(displaySize[0] - imguiInterval - self.imguiPos[0])
        self.imguiSize.append(displaySize[1] - screenPos[0][1] - imguiInterval - self.imguiPos[1])

        backgroundVerticesData = [
            0.0, 0.0, 5.0, 1.0, 0.0, 0.0, 0.5,
            screenPos[0][0], 0.0, 5.0, 1.0, 0.0, 0.0, 0.5,
            screenPos[0][0], displaySize[1], 5.0, 1.0, 0.0, 0.0, 0.5,
            0.0, displaySize[1], 5.0, 1.0, 0.0, 0.0, 0.5,

            screenPos[1][0], 0.0, 5.0, 1.0, 0.0, 0.0, 0.5,
            displaySize[0], 0.0, 5.0, 1.0, 0.0, 0.0, 0.5,
            displaySize[0], displaySize[1], 5.0, 1.0, 0.0, 0.0, 0.5,
            screenPos[1][0], displaySize[1], 5.0, 1.0, 0.0, 0.0, 0.5,

            0.0, 0.0, 5.0, 1.0, 0.0, 0.0, 0.5,
            displaySize[0], 0.0, 5.0, 1.0, 0.0, 0.0, 0.5,
            displaySize[0], screenPos[0][1], 5.0, 1.0, 0.0, 0.0, 0.5,
            0.0, screenPos[0][1], 5.0, 1.0, 0.0, 0.0, 0.5,

            0.0, screenPos[1][1], 5.0, 1.0, 0.0, 0.0, 0.5,
            displaySize[0], screenPos[1][1], 5.0, 1.0, 0.0, 0.0, 0.5,
            displaySize[0], displaySize[1], 5.0, 1.0, 0.0, 0.0, 0.5,
            0.0, displaySize[1], 5.0, 1.0, 0.0, 0.0, 0.5
            ]

        backgroundIndicesData = [
            0, 1, 2, 2, 3, 0,
            4, 5, 6, 6, 7, 4,
            8, 9, 10, 10, 11, 8,
            12, 13, 14, 14, 15, 12
            ]

        self.backgroundVertices = np.array(backgroundVerticesData, dtype = np.float32)
        self.backgroundIndices = np.array(backgroundIndicesData, dtype = np.uint32)

        backgroundLineVerticesData = [
            0.0, screenPos[0][1], 8.0, 1.0, 1.0, 1.0, 1.0,
            displaySize[0], screenPos[0][1], 8.0, 1.0, 1.0, 1.0, 1.0,

            0.0, screenPos[1][1], 8.0, 1.0, 1.0, 1.0, 1.0,
            displaySize[0], screenPos[1][1], 8.0, 1.0, 1.0, 1.0, 1.0,

            screenPos[0][0], 0.0, 8.0, 1.0, 1.0, 1.0, 1.0,
            screenPos[0][0], displaySize[1], 8.0, 1.0, 1.0, 1.0, 1.0,

            screenPos[1][0], 0.0, 8.0, 1.0, 1.0, 1.0, 1.0,
            screenPos[1][0], displaySize[1], 8.0, 1.0, 1.0, 1.0, 1.0
            ]

        backgroundLineIndicesData = [
            0, 1,
            2, 3,
            4, 5,
            6, 7
            ]

        self.backgroundLineVertices = np.array(backgroundLineVerticesData, dtype = np.float32)
        self.backgroundLineIndices = np.array(backgroundLineIndicesData, dtype = np.uint32)
        
        self.GUIStuffVerticesList.clear()
        self.GUIStuffIndicesList.clear()

        self.GUIStuffVerticesList.append(self.backgroundVertices)        
        self.GUIStuffVerticesList.append(self.backgroundLineVertices)        

        self.GUIStuffIndicesList.append(self.backgroundIndices)        
        self.GUIStuffIndicesList.append(self.backgroundLineIndices)        

        for i in range(self.numGUIStuff):
            glBindVertexArray(self.GUIVAO[i])

            glBindBuffer(GL_ARRAY_BUFFER, self.GUIVBO[i])
            glBufferData(GL_ARRAY_BUFFER, self.GUIStuffVerticesList[i].nbytes, self.GUIStuffVerticesList[i], GL_STATIC_DRAW)

            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.GUIEBO[i])
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.GUIStuffIndicesList[i].nbytes, self.GUIStuffIndicesList[i], GL_STATIC_DRAW)

            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, self.GUIStuffVerticesList[i].itemsize * self.numVertexComponents, ctypes.c_void_p(0))

            glEnableVertexAttribArray(1)
            glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, self.GUIStuffVerticesList[i].itemsize * self.numVertexComponents, ctypes.c_void_p(self.GUIStuffVerticesList[i].itemsize * 3))

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

        gSceneManager.AddSpecificProgramArgs(gSceneManager.GetColor('DefaultColor_', 7), [685, 17], 0, 1, 'Medium', self.programName)
        
    def _UpdateNewFrameImgui(self, deltaTime):
        imgui.new_frame()

        imgui.set_window_position_labeled('INFO', self.imguiPos[0], self.imguiPos[1], imgui.ONCE)
        imgui.set_window_size_named('INFO', self.imguiSize[0], self.imguiSize[1], imgui.ONCE)

        imgui.push_font(self.imguiNewFont)

        with imgui.begin('INFO', False, imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE):
            with imgui.begin_tab_bar('INFOTab'):
                if imgui.begin_tab_item('Render').selected:
                    if imgui.tree_node('Elememt'):
                        for key, value in self.imguiRenderElements.items():
                            _, value = imgui.checkbox(key, value)
                            self.imguiRenderElements[key] = value
                        imgui.tree_pop()
                    if imgui.tree_node('ViewType'):
                        for key, value in self.imguiRenderViewTypes.items():
                            _, value = imgui.checkbox(key, value)
                            self.imguiRenderViewTypes[key] = value
                        imgui.tree_pop()
                    imgui.end_tab_item()
                if imgui.begin_tab_item('Test').selected:
                    imgui.text('glPolygonOffset.(factor,units)')
                    values = [self.imguiTest['factor'], self.imguiTest['units']]
                    _, values = imgui.slider_float2(' ', *values, min_value = -10.0, max_value = 10.0, format = '%0.2f')
                    self.imguiTest['factor'] = values[0]
                    self.imguiTest['units'] = values[1]
                    imgui.separator()
                    values = [self.imguiTest['factor'], self.imguiTest['units']]
                    _, values[0] = imgui.input_float('factor', values[0], step = 0.1, format = '%0.2f')
                    _, values[1] = imgui.input_float('units', values[1], step = 0.1, format = '%0.2f')
                    self.imguiTest['factor'] = values[0]
                    self.imguiTest['units'] = values[1]
                    imgui.end_tab_item()                    
        
        imgui.pop_font()

    def _DrawCube(self):
        glPushAttrib(GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT)

        glEnable(GL_BLEND)

        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        transMat = glm.translate(glm.vec3(0.0, 0.0, 0.0))
        
        rotXMat = glm.rotate(glm.radians(self.rotDegree), glm.vec3(1.0, 0.0, 0.0))
        rotYMat = glm.rotate(glm.radians(self.rotDegree), glm.vec3(0.0, 1.0, 0.0))
        rotZMat = glm.rotate(glm.radians(self.rotDegree), glm.vec3(0.0, 0.0, 1.0))
        rotMat = rotZMat * rotYMat * rotXMat
        #rotMat = glm.mat4()
       
        scaleMat = glm.scale(glm.vec3(1.0, 1.0, 1.0))

        self.modelMat = transMat * rotMat * scaleMat

        shader = gSceneManager.GetShader()
        shader.SetMat4('modelMat', self.modelMat) 
        shader.SetBool('useUniformColor', False)

        glBindVertexArray(self.drawingStuffVAO[0])
        glDrawElements(GL_TRIANGLES, len(self.drawingStuffIndicesList[0]), GL_UNSIGNED_INT, None)

        glBindVertexArray(0)

        glPopAttrib()
        
    def _DrawModel(self):
        glPushAttrib(GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT | GL_POINT_BIT | GL_LINE_BIT | GL_POLYGON_BIT)

        glEnable(GL_BLEND)

        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        transMat = glm.translate(glm.vec3(0.5, -2.0, 6.0))

        rotXMat = glm.rotate(glm.radians(self.rotDegree), glm.vec3(1.0, 0.0, 0.0))
        rotYMat = glm.rotate(glm.radians(self.rotDegree), glm.vec3(0.0, 1.0, 0.0))
        rotZMat = glm.rotate(glm.radians(self.rotDegree), glm.vec3(0.0, 0.0, 1.0))
        #rotMat = rotXMat
        rotMat = glm.mat4()

        scaleMat = glm.scale(glm.vec3(20.0, 20.0, 20.0))

        self.modelMat = transMat * rotMat * scaleMat

        shader = gSceneManager.GetShader()
        shader.SetMat4('modelMat', self.modelMat)        
        shader.SetBool('useUniformColor', True)

        if self.imguiRenderElements['Face'] == True:
            glCullFace(GL_BACK)

            shader.SetVec4('uniformColor', 1.0, 0.0, 0.0, 1.0)
            glPolygonMode(GL_FRONT, GL_FILL)

            glBindVertexArray(self.drawingStuffVAO[0])
            glDrawElements(GL_TRIANGLES, len(self.drawingStuffIndicesList[0]), GL_UNSIGNED_INT, None)

        if self.imguiRenderViewTypes['BackFace'] == True:
            glCullFace(GL_FRONT)

            shader.SetVec4('uniformColor', 0.0, 1.0, 0.0, 1.0)
            glPolygonMode(GL_BACK, GL_FILL)

            glBindVertexArray(self.drawingStuffVAO[0])
            glDrawElements(GL_TRIANGLES, len(self.drawingStuffIndicesList[0]), GL_UNSIGNED_INT, None)

        if self.imguiRenderElements['Edge'] == True:
            glDisable(GL_CULL_FACE)

            glEnable(GL_POLYGON_OFFSET_LINE)
            #glPolygonOffset(self.imguiTest['factor'], self.imguiTest['units'])
            glPolygonOffset(-0.5, 0.0)

            shader.SetVec4('uniformColor', 1.0, 1.0, 1.0, 1.0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

            glLineWidth(1.0)

            glBindVertexArray(self.drawingStuffVAO[0])
            glDrawElements(GL_TRIANGLES, len(self.drawingStuffIndicesList[0]), GL_UNSIGNED_INT, None)

        if self.imguiRenderElements['Vertex'] == True:
            glEnable(GL_POINT_SMOOTH)
            glPointSize(5.0)

            shader.SetVec4('uniformColor', 0.0, 0.0, 1.0, 1.0)

            glBindVertexArray(self.drawingStuffVAO[0])
            glDrawArrays(GL_POINTS, 0, self.models[0].GetNumVertices())

        if self.imguiRenderElements['Normal'] == True:
            shader.SetVec4('uniformColor', 1.0, 1.0, 0.0, 1.0)

            glLineWidth(1.0)

            glBindVertexArray(self.drawingStuffVAO[1])
            glDrawElements(GL_LINES, len(self.drawingStuffIndicesList[1]), GL_UNSIGNED_INT, None)

        glBindVertexArray(0)

        glPopAttrib()
        
    def _DrawDrawingStuff(self):
        if self.objectType == 0:
            self._DrawCube()
        elif self.objectType == 5:
            self._DrawModel()

    def _DrawGUI(self):
        glPushAttrib(GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT | GL_LINE_BIT)

        glDisable(GL_DEPTH_TEST)

        glEnable(GL_BLEND)

        glBlendFunc(GL_SRC_ALPHA, GL_ZERO)

        shader = gSceneManager.GetShader()
        shader.SetMat4('modelMat', self.GUIModelMat)
        shader.SetBool('useUniformColor', False)

        GUIStuffIndex = 0
        
        glBindVertexArray(self.GUIVAO[GUIStuffIndex])
        glDrawElements(GL_TRIANGLES, len(self.GUIStuffIndicesList[GUIStuffIndex]), GL_UNSIGNED_INT, None)        
        
        GUIStuffIndex += 1

        glLineWidth(2.0)

        glBindVertexArray(self.GUIVAO[GUIStuffIndex])
        glDrawElements(GL_LINES, len(self.GUIStuffIndicesList[GUIStuffIndex]), GL_UNSIGNED_INT, None)
        
        glBindVertexArray(0)

        glPopAttrib()


def HandleWindowSizeCallback(glfwWindow, width, height):
    glViewport(0, 0, width, height)

    gSceneManager.SetDisplaySize(width, height)

def HandleKeyCallback(glfwWindow, key, scanCode, action, modes):
    if action == glfw.PRESS:
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(glfwWindow, glfw.TRUE)
        elif key == glfw.KEY_SPACE:
            gInputManager.SetKeyState(glfw.KEY_SPACE, True)

        if key == glfw.KEY_1:
            gInputManager.SetKeyState(glfw.KEY_1, True)
        elif key == glfw.KEY_2:
            gInputManager.SetKeyState(glfw.KEY_2, True)
        elif key == glfw.KEY_3:
            gInputManager.SetKeyState(glfw.KEY_3, True)
        elif key == glfw.KEY_4:
            gInputManager.SetKeyState(glfw.KEY_4, True)
        elif key == glfw.KEY_8:
            gInputManager.SetKeyState(glfw.KEY_8, True)
        elif key == glfw.KEY_9:
            gInputManager.SetKeyState(glfw.KEY_9, True)
        elif key == glfw.KEY_0:
            gInputManager.SetKeyState(glfw.KEY_0, True)

        if key == glfw.KEY_B:
            gInputManager.SetKeyState(glfw.KEY_B, True)        
        elif key == glfw.KEY_F:
            gInputManager.SetKeyState(glfw.KEY_F, True)        
        elif key == glfw.KEY_I:
            gInputManager.SetKeyState(glfw.KEY_I, True) 
        elif key == glfw.KEY_P:
            gInputManager.SetKeyState(glfw.KEY_P, True)            
        elif key == glfw.KEY_R:
            gInputManager.SetKeyState(glfw.KEY_R, True)        
        elif key == glfw.KEY_V:
            gInputManager.SetKeyState(glfw.KEY_V, True)
        elif key == glfw.KEY_X:
            gInputManager.SetKeyState(glfw.KEY_X, True)

        if key == glfw.KEY_W:
            gInputManager.SetKeyState(glfw.KEY_W, True)
        elif key == glfw.KEY_S:
            gInputManager.SetKeyState(glfw.KEY_S, True)
        elif key == glfw.KEY_A:
            gInputManager.SetKeyState(glfw.KEY_A, True)
        elif key == glfw.KEY_D:
            gInputManager.SetKeyState(glfw.KEY_D, True)
        elif key == glfw.KEY_Q:
            gInputManager.SetKeyState(glfw.KEY_Q, True)
        elif key == glfw.KEY_E:
            gInputManager.SetKeyState(glfw.KEY_E, True)

        if key == glfw.KEY_LEFT:
            gInputManager.SetKeyState(glfw.KEY_LEFT, True)
        elif key == glfw.KEY_RIGHT:
            gInputManager.SetKeyState(glfw.KEY_RIGHT, True)
        elif key == glfw.KEY_UP:
            gInputManager.SetKeyState(glfw.KEY_UP, True)
        elif key == glfw.KEY_DOWN:
            gInputManager.SetKeyState(glfw.KEY_DOWN, True)

    if action == glfw.RELEASE:
        if key == glfw.KEY_W:
            gInputManager.SetKeyState(glfw.KEY_W, False)
        elif key == glfw.KEY_S:
            gInputManager.SetKeyState(glfw.KEY_S, False)
        elif key == glfw.KEY_A:
            gInputManager.SetKeyState(glfw.KEY_A, False)
        elif key == glfw.KEY_D:
            gInputManager.SetKeyState(glfw.KEY_D, False)
        elif key == glfw.KEY_Q:
            gInputManager.SetKeyState(glfw.KEY_Q, False)
        elif key == glfw.KEY_E:
            gInputManager.SetKeyState(glfw.KEY_E, False)

        if key == glfw.KEY_LEFT:
            gInputManager.SetKeyState(glfw.KEY_LEFT, False)
        elif key == glfw.KEY_RIGHT:
            gInputManager.SetKeyState(glfw.KEY_RIGHT, False)
        elif key == glfw.KEY_UP:
            gInputManager.SetKeyState(glfw.KEY_UP, False)
        elif key == glfw.KEY_DOWN:
            gInputManager.SetKeyState(glfw.KEY_DOWN, False)

def HandleMouseButtonCallback(glfwWindow, button, action, mod):
    if button == glfw.MOUSE_BUTTON_LEFT:
        if action == glfw.PRESS:            
            gInputManager.SetMouseButtonClick(glfw.MOUSE_BUTTON_LEFT, True)
            gInputManager.SetLastMousePosOnClick(glfw.get_cursor_pos(glfwWindow))
        elif action == glfw.RELEASE:            
            gInputManager.SetMouseButtonClick(glfw.MOUSE_BUTTON_LEFT, False)

    if button == glfw.MOUSE_BUTTON_RIGHT:
        if action == glfw.PRESS:
            gInputManager.SetMouseButtonClick(glfw.MOUSE_BUTTON_RIGHT, True)            

            screenPos = gSceneManager.GetScreenPos()
            mousePos = glfw.get_cursor_pos(glfwWindow)

            gInputManager.SetLastMousePosOnClick(mousePos)

            if mousePos[0] < screenPos[0][0] or screenPos[1][0] < mousePos[0]:
                gSceneManager.SetEnableCameraMove(False)
            elif mousePos[1] < screenPos[0][1] or screenPos[1][1] < mousePos[1]:
                gSceneManager.SetEnableCameraMove(False)
            else:
                gSceneManager.SetEnableCameraMove(True)
                gInputManager.SetLastMousePos(mousePos)

        elif action == glfw.RELEASE:
            gSceneManager.SetEnableCameraMove(False)
            gInputManager.SetMouseButtonClick(glfw.MOUSE_BUTTON_RIGHT, False)            

def HandleCursorPosCallback(glfwWindow, xPos, yPos):
    screenPos = gSceneManager.GetScreenPos()

    if xPos < screenPos[0][0] or screenPos[1][0] < xPos:
        gInputManager.SetMouseEntered(False)
    elif yPos < screenPos[0][1] or screenPos[1][1] < yPos:
        gInputManager.SetMouseEntered(False)
    else:
        gInputManager.SetMouseEntered(True)

    if gSceneManager.GetEnableCameraMove() == True:
        lastPos = gInputManager.GetLastMousePos()
        xOffset = lastPos[0] - xPos
        yOffset = lastPos[1] - yPos

        gInputManager.SetLastMousePos([xPos, yPos])

        camera = gSceneManager.GetCamera()

        if gSceneManager.GetView3D() == True:
            camera.ProcessMouseMovement(xOffset, yOffset)

        displaySize = gSceneManager.GetDisplaySize()   
    
        mouseCheckInterval = 20

        if xPos < 0:
            glfw.set_cursor_pos(glfwWindow, displaySize[0] - mouseCheckInterval, yPos)
            gInputManager.SetLastMousePos(glfw.get_cursor_pos(glfwWindow))
        elif xPos > displaySize[0]:
            glfw.set_cursor_pos(glfwWindow, mouseCheckInterval, yPos)
            gInputManager.SetLastMousePos(glfw.get_cursor_pos(glfwWindow))

        if yPos < 0:
            glfw.set_cursor_pos(glfwWindow, xPos, displaySize[1] - mouseCheckInterval)
            gInputManager.SetLastMousePos(glfw.get_cursor_pos(glfwWindow))
        elif yPos > displaySize[1]:
            glfw.set_cursor_pos(glfwWindow, xPos, mouseCheckInterval)
            gInputManager.SetLastMousePos(glfw.get_cursor_pos(glfwWindow))

        gSceneManager.SetDirty(True)
        
    else:
        gInputManager.SetLastMousePos([xPos, yPos])

    #print('LastMousePosOnClick : {0}'.format(gInputManager.GetLastMousePosOnClick()))
    #print('LastMousePos : {0}'.format(gInputManager.GetLastMousePos()))

def InitializeGLFW(projectName):
    displaySize = gSceneManager.GetDisplaySize()

    if not glfw.init():
        return

    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)

    glfwWindow = glfw.create_window(displaySize[0], displaySize[1], projectName, None, None)

    if not glfwWindow:
        glfw.terminate()
        return

    videoMode = glfw.get_video_mode(glfw.get_primary_monitor())

    windowWidth = videoMode.size.width
    windowHeight = videoMode.size.height
    windowPosX = int(windowWidth / 2 - displaySize[0] / 2) - 250
    windowPosY = int(windowHeight / 2 - displaySize[1] / 2) - 50

    glfw.set_window_pos(glfwWindow, windowPosX, windowPosY)

    glfw.show_window(glfwWindow)    

    glfw.make_context_current(glfwWindow)

    glfw.set_window_size_callback(glfwWindow, HandleWindowSizeCallback)

    glfw.set_key_callback(glfwWindow, HandleKeyCallback) 

    glfw.set_mouse_button_callback(glfwWindow, HandleMouseButtonCallback)
    
    glfw.set_cursor_pos_callback(glfwWindow, HandleCursorPosCallback)

    return glfwWindow

def Main():    
    projectName = "TEST PROJECT"
    programName = "# ModelLoading"

    glfwWindow = InitializeGLFW(projectName)

    imgui.create_context()
    imguiRenderer = GlfwRenderer(glfwWindow, False)

    io = imgui.get_io()
    imguiNewFont = io.fonts.add_font_from_file_ttf('../../Resource/Font/comic.ttf', 14)
    imguiRenderer.refresh_font_texture()    

    shader = Shader(vertexShaderCode, fragmentShaderCode)

    gSceneManager.InitializeOpenGL(shader)
    gSceneManager.SetCamera(Camera())
    gSceneManager.MakeFont()    
    gSceneManager.AddObject(TestProgram(programName, imguiNewFont))
    
    lastElapsedTime = glfw.get_time()
    deltaTime = 0.0

    while glfw.window_should_close(glfwWindow) == False:
        glfw.poll_events()        
        imguiRenderer.process_inputs()

        gSceneManager.Update(deltaTime)        

        gSceneManager.Draw()

        imgui.render()
        imguiRenderer.render(imgui.get_draw_data())

        glfw.swap_buffers(glfwWindow)

        gSceneManager.PostUpdate(deltaTime)        

        deltaTime = glfw.get_time() - lastElapsedTime
        lastElapsedTime = glfw.get_time()

    imguiRenderer.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    Main()   