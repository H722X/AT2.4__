# coding=utf-8
import time
import pymel.core as pm
import maya.OpenMaya as om
import logging
import re
import math


debug = False
debugZero = False
_logger = logging.getLogger(__name__)


class FkIk_UI:
    COLOR_PRESETS = {
        "grey": (.5, .5, .5),
        "lightgrey": (.7, .7, .7),
        "darkgrey": (.2, .2, .2),
        "turquoise": (.3, .55, .55),
        "lightBlue": (0.588, 0.674, 0.765),
        "darkGreen": (0.082, 0.243, 0.267),
        "lightGreen": [(.537, .694, .6), (.631, .753, .667), (.804, .882, .839), (.851, .902, .882)]
    }
    IK_FK = ['_IK', 'IK_', '_IK_', '_FK', '_FK_', 'FK_']
    arm_leg = {'arm': ['Arm', 'arm', 'Blender'], 'leg': ['Leg', 'leg'], 'L': ['_L', 'L_', '_l', 'l_', '_L_', '_l_', 'lf', 'Lf', 'left'],
               'R': ['_R', 'R_', '_r', 'r_', '_R_', '_r_', 'rt', 'Rt', 'right']}

    CTRL_NAME_INI = {
    'arm': {
            'FK1': ['UpperArm', 'shldr', 'Shoulder', 'ShoulderControl', 'FKShoulder', 'arm_1', 'fk_1'],
            'FK2': ['Forearm', 'elbow', 'ElbowControl', 'FKElbow', 'arm_2', 'fk_2'],
            'FK3': ['Hand', 'wrist', 'WristControl', 'FKWrist', 'fkHand', 'arm_3', 'fk_3'],
            'IK1': ['Hand', 'HandCTRL', 'ikHand', 'IKArm', 'arm'],
            'IK2': ['elbow', 'pv', 'PVCTRL', 'PoleArm', 'polevector']
          },
     'leg': {
            'FK1': ['Thigh', 'hip', 'FKHip', 'leg_1', 'fk_1'],
            'FK2': ['Calf', 'knee', 'FKKnee', 'leg_2', 'fk_2'],
            'FK3': ['Foot', 'ankle', 'FKAnkle', 'leg_3', 'fk_3'],
            'IK1': ['ankle', 'Foot', 'IKLeg', 'leg'],
            'IK2': ['knee', 'pv', 'PoleLeg', 'polevector']
          }
    }


    def __init__(self):
        global win
        win = 'ikfkswitchUI_'

        global gMainProgressBar
        gMainProgressBar = pm.mel.eval('$tmp = $gMainProgressBar')

        # logging.basicConfig(level=logging.INFO)
        _logger.disabled = not debug

        if pm.window("Auto_ikFk_UI", exists=True):
            pm.deleteUI("Auto_ikFk_UI")
        windowWidth = 230
        windowHeight = 200

        window = pm.window("Auto_ikFk_UI", tlb=True, width=windowWidth, height=windowHeight, title="Auto IK FK")
        topLevelColumn = pm.columnLayout(adjustableColumn=True, columnAlign="center")

        # Setup Tabs #every child creates new tab
        tabHeight = 250
        tabWidth = 220
        # scrollWidth = tabWidth - 40

        riggTab = self.initializeTab(tabHeight, tabWidth)
        pm.setParent("..")

        # 创建计划
        pm.scriptJob(event=['SceneOpened', self.color_text], p=window)

        # Display window
        pm.showWindow("Auto_ikFk_UI")

    def initializeTab(self, tabHeight, tabWidth):
        frameWidth = tabWidth - 20
        mainColumnLayout = pm.columnLayout(win + "mainColumnLayout", w=tabWidth, columnAttach=('left', 10))
        pm.setParent(win + "mainColumnLayout")
        pm.separator(h=10)
        pm.button(label='AUTO Match IK_FK', w=200, command=lambda a: self.save_data())

        pm.separator(h=5)
        pm.rowColumnLayout(win + "info", numberOfColumns=4, columnWidth=[(1, 50), (2, 50), (3, 50), (4, 50)])

        self.readyText_L_Arm = pm.text(win + 'readyText_LArm', label='', align='center', w=40, h=20,
                                       bgc=self.COLOR_PRESETS["darkgrey"])
        self.readyText_R_Arm = pm.text(win + 'readyText_RArm', label='', align='center', w=40,
                                       bgc=self.COLOR_PRESETS["darkgrey"])
        self.readyText_L_Leg = pm.text(win + 'readyText_LLeg', label='', align='center', w=40,
                                       bgc=self.COLOR_PRESETS["darkgrey"])
        self.readyText_R_Leg = pm.text(win + 'readyText_RLeg', label='', align='center', w=40,
                                       bgc=self.COLOR_PRESETS["darkgrey"])
        self.color_text()
        pm.setParent(win + "mainColumnLayout")
        pm.separator(h=10)

        pm.rowColumnLayout(win + "matchIKRow", columnWidth=[(1, 200)])
        self.dropdown = pm.optionMenu(label="Mode")
        # pm.menuItem(label="CtrlMode")
        pm.menuItem(label="JointMode")
        pm.menuItem(label="CtrlMode")
        pm.button(label="AUTO IK_FK", bgc=self.COLOR_PRESETS["darkGreen"],
                  command=lambda a: self.on_button_clicked())

        pm.popupMenu()
        pm.menuItem(label="FK", command=lambda a: self.on_button_clicked(to_fk=1, auto=False))
        pm.menuItem(label="IK", command=lambda a: self.on_button_clicked(to_fk=0, auto=False))
        pm.menuItem(label="Batch FK", command=lambda a: self.batch_Mode(to_fk=1))
        pm.menuItem(label="Batch IK", command=lambda a: self.batch_Mode(to_fk=0))
        pm.setParent(win + "mainColumnLayout")

        pm.rowColumnLayout(win + "switchIKRow", numberOfColumns=2, columnWidth=[(1, 100), (2, 100)])
        pm.button(label="AUTO Switch", command=lambda a: self.switch_ik_fk(auto=True))
        pm.popupMenu()
        pm.menuItem(label="Switch IK", command=lambda a: self.switch_ik_fk(fk=False))
        pm.menuItem(label="Switch FK", command=lambda a: self.switch_ik_fk(fk=True))

        pm.button(label="Select All", command=lambda a: self.select_All(mode='all'))
        pm.popupMenu()
        pm.menuItem(label="Select All IK", command=lambda a: self.select_All(mode='ik'))
        pm.menuItem(label="Select All FK", command=lambda a: self.select_All(mode='fk'))
        pm.setParent(win + "mainColumnLayout")

        pm.separator(h=20)
        pm.text('Release 1.00(Beta)                 AUTO_IKFK                  copyright H.2024')
        pm.separator(h=5)
        pm.window('Auto_ikFk_UI', e=True, width=230, height=160)

    # 下拉选项
    def on_button_clicked(self, to_fk=1, auto=True):
        selected_option = pm.optionMenu(self.dropdown, query=True, value=True)
        if selected_option == "CtrlMode":
            if auto:
                self.matchIkFk_Auto(to_fk=1, auto=True, mode='ctrlMode')
            elif to_fk == 1:
                self.matchIkFk_Auto(to_fk=1, auto=False, mode='ctrlMode')
            elif to_fk == 0:
                self.matchIkFk_Auto(to_fk=0, auto=False, mode='ctrlMode')
        elif selected_option == "JointMode":
            if auto:
                self.matchIkFk_Auto(to_fk=1, auto=True, mode='jointMode')
            elif to_fk == 1:
                self.matchIkFk_Auto(to_fk=1, auto=False, mode='jointMode')
            elif to_fk == 0:
                self.matchIkFk_Auto(to_fk=0, auto=False, mode='jointMode')

    # 批量_模式
    def batch_Mode(self, to_fk=1):
        selected_option = pm.optionMenu(self.dropdown, query=True, value=True)
        if selected_option == "CtrlMode":
            if to_fk == 1:
                self.batch_IK_FK(ik=False, mode='ctrlMode')
            elif to_fk == 0:
                self.batch_IK_FK(ik=True, mode='ctrlMode')
        elif selected_option == "JointMode":
            if to_fk == 1:
                self.batch_IK_FK(ik=False, mode='jointMode')
            elif to_fk == 0:
                self.batch_IK_FK(ik=True, mode='jointMode')

    # 检测数据，标记颜色===================================================================================================
    # {'L_arm': L_arm, 'R_arm': R_arm, 'L_leg': L_leg, 'R_leg': R_leg}
    def color_text(self):
        sel = pm.ls(sl=True)
        if sel:
            if ':' in sel[-1]:
               spaceName = sel[-1].split(':')[0]
            else:
                spaceName = 'SpaceNameNull'

            if pm.objExists(spaceName + '_AUTO_IK_FK_NETWORK.notes'):
                data = dict(eval(str(pm.getAttr(spaceName + '_AUTO_IK_FK_NETWORK.notes'))))
                if data['L_arm']:
                    if '' not in data['L_arm']:
                        pm.text(self.readyText_L_Arm, edit=True, label='L_Arm', bgc=self.COLOR_PRESETS["lightGreen"][0])
                else:
                    pm.text(self.readyText_L_Arm, edit=True, label='', bgc=self.COLOR_PRESETS["darkgrey"])
                if data['R_arm']:
                    if '' not in data['R_arm']:
                        pm.text(self.readyText_R_Arm, edit=True, label='R_Arm', bgc=self.COLOR_PRESETS["lightGreen"][1])
                else:
                    pm.text(self.readyText_R_Arm, edit=True, label='', bgc=self.COLOR_PRESETS["darkgrey"])
                if data['L_leg']:
                    if '' not in data['L_leg']:
                        pm.text(self.readyText_L_Leg, edit=True, label='L_Leg', bgc=self.COLOR_PRESETS["lightGreen"][2])
                else:
                    pm.text(self.readyText_L_Leg, edit=True, label='', bgc=self.COLOR_PRESETS["darkgrey"])
                if data['R_leg']:
                    if '' not in data['R_leg']:
                        pm.text(self.readyText_R_Leg, edit=True, label='R_Leg', bgc=self.COLOR_PRESETS["lightGreen"][3])
                else:
                    pm.text(self.readyText_R_Leg, edit=True, label='', bgc=self.COLOR_PRESETS["darkgrey"])
            else:
                pm.text(self.readyText_L_Arm, edit=True, label='', bgc=self.COLOR_PRESETS["darkgrey"])
                pm.text(self.readyText_R_Arm, edit=True, label='', bgc=self.COLOR_PRESETS["darkgrey"])
                pm.text(self.readyText_L_Leg, edit=True, label='', bgc=self.COLOR_PRESETS["darkgrey"])
                pm.text(self.readyText_R_Leg, edit=True, label='', bgc=self.COLOR_PRESETS["darkgrey"])
        else:
            if pm.objExists('*_AUTO_IK_FK_NETWORK.notes'):
                pm.text(self.readyText_L_Arm, edit=True, label='', bgc=self.COLOR_PRESETS["lightGreen"][0])
                pm.text(self.readyText_R_Arm, edit=True, label='', bgc=self.COLOR_PRESETS["lightGreen"][1])
                pm.text(self.readyText_L_Leg, edit=True, label='', bgc=self.COLOR_PRESETS["lightGreen"][2])
                pm.text(self.readyText_R_Leg, edit=True, label='', bgc=self.COLOR_PRESETS["lightGreen"][3])
            else:
                pm.text(self.readyText_L_Arm, edit=True, label='', bgc=self.COLOR_PRESETS["darkgrey"])
                pm.text(self.readyText_R_Arm, edit=True, label='', bgc=self.COLOR_PRESETS["darkgrey"])
                pm.text(self.readyText_L_Leg, edit=True, label='', bgc=self.COLOR_PRESETS["darkgrey"])
                pm.text(self.readyText_R_Leg, edit=True, label='', bgc=self.COLOR_PRESETS["darkgrey"])

    # b对齐a
    @staticmethod
    def align_obj(a, b):
        temp_con = pm.parentConstraint([a, b])
        pm.delete(temp_con)

    # 创建Loc在对象的位置
    @staticmethod
    def loc_create(obj):
        loc = pm.spaceLocator()
        con = pm.parentConstraint([obj, loc])
        pm.delete(con)
        return loc

    # 计算两对象间的偏移值
    def offset_V(self, obj1, obj2):
        loc1 = self.loc_create(obj1)
        loc2 = self.loc_create(obj2)
        pm.parent(loc2, loc1)
        T = pm.getAttr(loc2 + '.translate')
        T = [float(T[0]), float(T[1]), float(T[2])]
        R = pm.getAttr(loc2 + '.rotate')
        R = [float(R[0]), float(R[1]), float(R[2])]
        pm.delete([loc1, loc2])
        return list(T) + list(R)


    # 距离计算a到b
    @staticmethod
    def distance(a, b):
        d_a = pm.xform(a, q=True, ws=True, t=True)
        d_b = pm.xform(b, q=True, ws=True, t=True)
        d = [d_a[0]-d_b[0], d_a[1]-d_b[1], d_a[2]-d_b[2]]
        return math.sqrt(sum(x ** 2 for x in d))

    # 查询对象是否隐藏
    def isObjectHidden(self, objectName):
        # 获取物体的显示状态
        isVisible = pm.getAttr(objectName + ".visibility")
        if isVisible:
            parent = pm.listRelatives(objectName, parent=True, fullPath=True)
            while parent:
                ex = pm.objExists(parent[0] + ".visibility")
                if not ex:
                    parent = pm.listRelatives(parent[0], parent=True, fullPath=False)
                    continue
                elif pm.getAttr(parent[0] + ".visibility") == False:
                    return True
                    break
                else:
                    parent = pm.listRelatives(parent[0], parent=True, fullPath=True)
                    if not parent:
                        return False
                    continue

        else:  # 如果物体和所有父节点都显示，则物体未隐藏
            return True

    # 获取层级下所有曲线
    def get_curve(self, inputCurve):
        selectionList = om.MSelectionList()  # 创建一个空的选择列表
        for obj in inputCurve:
            selectionList.add(obj)
        # selectionList = om.MSelectionList()
        # om.MGlobal.getActiveSelectionList(selectionList)
        sel = []
        # 遍历选择的对象
        for i in range(selectionList.length()):
            dagPath = om.MDagPath()
            selectionList.getDagPath(i, dagPath)
            # 获取层级下所有的曲线
            dagIterator = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kNurbsCurve)
            dagIterator.reset(dagPath.node(), om.MItDag.kDepthFirst, om.MFn.kNurbsCurve)
            while not dagIterator.isDone():
                curveDagPath = om.MDagPath()
                dagIterator.getPath(curveDagPath)
                transformNode = curveDagPath.transform()
                transformNodeFn = om.MFnDagNode(transformNode)
                sel.append(transformNodeFn.name())

                dagIterator.next()
        return sel

    # 递归查询所有IK_FK连接到visibility属性的节点
    global vis
    vis = []
    def query_connect_ctrl(self, obj):
        global vis
        connect_attr = pm.listConnections(obj, p=True, s=False, scn=True)
        if connect_attr:
            for attr in connect_attr:
                name_attr = attr.split('.')
                if pm.objectType(attr) == 'transform':
                    if name_attr[1] == 'visibility':
                        vis.append(name_attr[0])
                    self.query_connect_ctrl(name_attr[0])
                elif pm.objectType(attr) == 'joint':
                    if name_attr[1] == 'visibility':
                        vis.append(name_attr[0])
                else:
                    if pm.attributeQuery('output', node=name_attr[0], exists=True):
                        self.query_connect_ctrl(name_attr[0])

    # 自动化获取相关对象及属性:FK1,FK2,FK3,IK Ctrl,IK Pole,switchCtrl, switchAttr,switch0isfk, switchAttrRange, rotOffset, bendKneeAxis, [joint], [joint_offset]
    def autoGetInput(self, sel_ctrl, L_or_R, arm_or_leg, joint_lst):
        global vis
        inputValues = ['', '', '', '', '', '', '', '', '', '', '', [], [], []]
        inputValues[11] = joint_lst
        inputValues[5] = str(sel_ctrl)
        ctrl_vis = []
        # 获取ik_fk属性
        attr = pm.channelBox("mainChannelBox", query=True, selectedMainAttributes=True)
        if attr is not None:
            inputValues[6] = '%s.%s' % (sel_ctrl, attr[0])
            if pm.attributeQuery(attr[0], node=sel_ctrl, re=True):
                ik_fk_range = pm.attributeQuery(attr[0], node=sel_ctrl, range=True)
                inputValues[8] = int(ik_fk_range[1])
            else:
                ik_fk_current = pm.getAttr(inputValues[6])
                pm.setAttr(inputValues[6], 100)
                ik_fk_max = pm.getAttr(inputValues[6])
                inputValues[8] = int(ik_fk_max)
                pm.setAttr(inputValues[6], ik_fk_current)

            # 获取属性相关的曲线控制器===============================================================
            ik_fk_connect_attr = pm.listConnections(sel_ctrl+'.'+attr[0], p=True, s=False)
            for first_connect_attr in ik_fk_connect_attr:
                name_attr = first_connect_attr.split('.')
                if name_attr[1] == 'visibility':
                    ctrl_vis.append(name_attr[0])
                self.query_connect_ctrl(name_attr[0])
                ctrl_vis += vis
            ctrl_vis = self.get_curve(ctrl_vis)
            ctrl_vis = list(dict.fromkeys(ctrl_vis))
            vis = []
            # 分出FK1,FK2,FK3,IK Ctrl,IK Pole
            for ctrl in ctrl_vis:
                if ':' in ctrl:
                    ctrl_ = ctrl.replace(':', '_')
                else:
                    ctrl_ = ctrl
                if arm_or_leg == 'arm':
                    I_F = re.findall(r"ik|fk", str(ctrl), re.I)
                    if I_F:
                        I_F = I_F[0]
                    else:
                        I_F = ''
                    if True in [i.upper() in [(ctrl_.split('_')[x_i-1] + '_' + x).upper() if x.isdigit() else x.upper() for x_i, x in enumerate(ctrl_.split('_'))] for i in self.CTRL_NAME_INI['arm']['FK1']]:
                        if I_F == '':
                            inputValues[0] = ctrl
                        else:
                            if I_F.upper() == 'FK':
                                if inputValues[0]:
                                    if len(ctrl) < len(inputValues[0]):
                                        if not False in [i in inputValues[0].split('_') for i in ctrl.split('_')]:
                                            inputValues[0] = ctrl
                                else:
                                    inputValues[0] = ctrl
                    if True in [i.upper() in [(ctrl_.split('_')[x_i-1] + '_' + x).upper() if x.isdigit() else x.upper() for x_i, x in enumerate(ctrl_.split('_'))] for i in self.CTRL_NAME_INI['arm']['FK2']]:
                        if I_F == '':
                            inputValues[1] = ctrl
                        else:
                            if I_F.upper() == 'FK':
                                if inputValues[1]:
                                    if len(ctrl) < len(inputValues[1]):
                                        if not False in [i in inputValues[1].split('_') for i in ctrl.split('_')]:
                                            inputValues[1] = ctrl
                                else:
                                    inputValues[1] = ctrl
                    if True in [i.upper() in [(ctrl_.split('_')[x_i-1] + '_' + x).upper() if x.isdigit() else x.upper() for x_i, x in enumerate(ctrl_.split('_'))] for i in self.CTRL_NAME_INI['arm']['FK3']]:
                        if I_F == '':
                            inputValues[2] = ctrl
                        else:
                            if I_F.upper() == 'FK':
                                if inputValues[2]:
                                    if len(ctrl) < len(inputValues[2]):
                                        if not False in [i in inputValues[2].split('_') for i in ctrl.split('_')]:
                                            inputValues[2] = ctrl
                                else:
                                    inputValues[2] = ctrl
                    if True in [i.upper() in [(ctrl_.split('_')[x_i-1] + '_' + x).upper() if x.isdigit() else x.upper() for x_i, x in enumerate(ctrl_.split('_'))] for i in self.CTRL_NAME_INI['arm']['IK1']]:
                            if I_F == '':
                                # inputValues[3] = ctrl
                                pass
                            else:
                                if I_F.upper() == 'IK':
                                    if inputValues[3]:
                                        if True in [i in inputValues[3].split('_') for i in self.CTRL_NAME_INI['leg']['IK1'][:-1]]:
                                            pass
                                        else:
                                            key_world_IK_hand = True
                                            if True in [i in ctrl.split('_') for i in self.CTRL_NAME_INI['leg']['IK1'][:-1]]:
                                                inputValues[3] = ctrl
                                            else:
                                                key_world_IK_hand = False
                                            if not key_world_IK_hand:
                                                if len(ctrl) < len(inputValues[3]):
                                                    # if not False in [i in inputValues[3].split('_') for i in ctrl.split('_')]:
                                                        inputValues[3] = ctrl
                                    else:
                                        inputValues[3] = ctrl
                    if True in [i.upper() in [(ctrl_.split('_')[x_i-1] + '_' + x).upper() if x.isdigit() else x.upper() for x_i, x in enumerate(ctrl_.split('_'))] for i in self.CTRL_NAME_INI['arm']['IK2']]:
                            if I_F == '':
                                inputValues[4] = ctrl
                            elif I_F.upper() == 'IK':
                                    inputValues[4] = ctrl

                if arm_or_leg == 'leg':
                    I_F = re.findall(r"ik|fk", str(ctrl), re.I)
                    if I_F:
                        I_F = I_F[0]
                    else:
                        I_F = ''
                    if True in [i.upper() in [(ctrl_.split('_')[x_i-1] + '_' + x).upper() if x.isdigit() else x.upper() for x_i, x in enumerate(ctrl_.split('_'))] for i in self.CTRL_NAME_INI['leg']['FK1']]:
                        if I_F == '':
                            inputValues[0] = ctrl
                        else:
                            if I_F.upper() == 'FK':
                                if inputValues[0]:
                                    if len(ctrl) < len(inputValues[0]):
                                        if not False in [i in inputValues[0].split('_') for i in ctrl.split('_')]:
                                            inputValues[0] = ctrl
                                else:
                                    inputValues[0] = ctrl
                    if True in [i.upper() in [(ctrl_.split('_')[x_i-1] + '_' + x).upper() if x.isdigit() else x.upper() for x_i, x in enumerate(ctrl_.split('_'))] for i in self.CTRL_NAME_INI['leg']['FK2']]:
                        if I_F == '':
                            inputValues[1] = ctrl
                        else:
                            if I_F.upper() == 'FK':
                                if inputValues[1]:
                                    if len(ctrl) < len(inputValues[1]):
                                        if not False in [i in inputValues[1].split('_') for i in ctrl.split('_')]:
                                            inputValues[1] = ctrl
                                else:
                                    inputValues[1] = ctrl
                    if True in [i.upper() in [(ctrl_.split('_')[x_i-1] + '_' + x).upper() if x.isdigit() else x.upper() for x_i, x in enumerate(ctrl_.split('_'))] for i in self.CTRL_NAME_INI['leg']['FK3']]:
                            if I_F == '':
                                inputValues[2] = ctrl
                            else:
                                if I_F.upper() == 'FK':
                                    if inputValues[2]:
                                        if len(ctrl) < len(inputValues[2]):
                                            if not False in [i in inputValues[2].split('_') for i in ctrl.split('_')]:
                                                inputValues[2] = ctrl
                                    else:
                                        inputValues[2] = ctrl
                    if True in [i.upper() in [(ctrl_.split('_')[x_i-1] + '_' + x).upper() if x.isdigit() else x.upper() for x_i, x in enumerate(ctrl_.split('_'))] for i in self.CTRL_NAME_INI['leg']['IK1']]:
                            if I_F == '':
                                # inputValues[3] = ctrl
                                pass
                            else:
                                if I_F.upper() == 'IK':
                                    if inputValues[3]:
                                        if True in [i in inputValues[3].split('_') for i in self.CTRL_NAME_INI['leg']['IK1'][:-1]]:
                                            pass
                                        else:
                                            key_world_IK_leg = True
                                            if True in [i in ctrl.split('_') for i in self.CTRL_NAME_INI['leg']['IK1'][:-1]]:
                                                inputValues[3] = ctrl
                                            else:
                                                key_world_IK_leg = False
                                            if not key_world_IK_leg:
                                                if len(ctrl) < len(inputValues[3]):
                                                    # if not False in [i in inputValues[3].split('_') for i in ctrl.split('_')]:
                                                        inputValues[3] = ctrl
                                    else:
                                        inputValues[3] = ctrl
                    if True in [i.upper() in [(ctrl_.split('_')[x_i-1] + '_' + x).upper() if x.isdigit() else x.upper() for x_i, x in enumerate(ctrl_.split('_'))] for i in self.CTRL_NAME_INI['leg']['IK2']]:
                        if inputValues[4] == '':
                            if I_F == '':
                                inputValues[4] = ctrl
                            elif I_F.upper() == 'IK':
                                inputValues[4] = ctrl

        ctrls_arm = ['upperArm', 'lowerArm', 'fkHand', 'ikHand', 'ikPole']
        ctrls_leg = ['thigh', 'calf', 'fkFoot', 'ikFoot', 'poleLeg']
        NO_FOUND = 0
        for i, v in enumerate(inputValues[0:5]):
            if not v:
                NO_FOUND = 1
                if L_or_R == 'L':
                    if arm_or_leg == 'arm':
                        pm.displayInfo('NO Ctrl Found L_{} !'.format(ctrls_arm[i]))
                    elif arm_or_leg == 'leg':
                        pm.displayInfo('NO Ctrl Found L_{} !'.format(ctrls_leg[i]))
                elif L_or_R == 'R':
                    if arm_or_leg == 'arm':
                        pm.displayInfo('NO Ctrl Found R_{} !'.format(ctrls_arm[i]))
                    elif arm_or_leg == 'leg':
                        pm.displayInfo('NO Ctrl Found R_{} !'.format(ctrls_leg[i]))
        if NO_FOUND:
            return ['NO Ctrl Found']
        # 判断0是否为FK==================================
        if int(pm.getAttr(inputValues[6])) == 0:
            judge = self.isObjectHidden(inputValues[0])
            if judge:
                inputValues[7] = 0
            else:
                inputValues[7] = 1
        else:
            judge = self.isObjectHidden(inputValues[0])
            if judge:
                inputValues[7] = 1
            else:
                inputValues[7] = 0

        # 获取偏移值====================================
        loc_f = pm.spaceLocator()
        loc_i = pm.spaceLocator()
        self.align_obj(inputValues[2], loc_f)
        self.align_obj(inputValues[3], loc_i)
        pm.parent(loc_i, loc_f)
        inputValues[9] = list(pm.getAttr(loc_i + ".rotate"))
        pm.delete([loc_f, loc_i])

        # IK2轴向====================================================================
        if (inputValues[0] != '') & (inputValues[1] != ''):
            loc_fk_1 = self.loc_create(inputValues[0])
            loc_fk_2 = self.loc_create(inputValues[1])
            pm.parent(loc_fk_2, loc_fk_1)
            loc_2_rotate = list(pm.getAttr(loc_fk_2 + '.rotate'))
            dict_loc_2_rotate = {'X': loc_2_rotate[0], 'Y': loc_2_rotate[1], 'Z': loc_2_rotate[2]}
            dict_loc_2_rotate_abs = {'X': abs(loc_2_rotate[0]), 'Y': abs(loc_2_rotate[1]), 'Z': abs(loc_2_rotate[2])}
            axial = max(dict_loc_2_rotate_abs, key=dict_loc_2_rotate_abs.get)
            if dict_loc_2_rotate[axial] < -0.5:
                inputValues[10] = '+' + axial
            elif dict_loc_2_rotate[axial] > 0.5:
                inputValues[10] = '-' + axial
            else:
                if (inputValues[1] != '') & (inputValues[2] != '') & (inputValues[4] != ''):
                    loc_fk2 = self.loc_create(inputValues[1])
                    loc_fk3 = self.loc_create(inputValues[2])
                    loc_ik2 = self.loc_create(inputValues[4])
                    pm.parent(loc_fk3, loc_fk2)
                    pm.parent(loc_fk2, inputValues[1])
                    # 旋转loc_fk2
                    pm.setAttr(loc_fk2.rotate, [90, 0, 0])
                    d_ax = self.distance(loc_fk3, loc_ik2)
                    pm.setAttr(loc_fk2.rotate, [-90, 0, 0])
                    d_px = self.distance(loc_fk3, loc_ik2)
                    pm.setAttr(loc_fk2.rotate, [0, 90, 0])
                    d_ay = self.distance(loc_fk3, loc_ik2)
                    pm.setAttr(loc_fk2.rotate, [0, -90, 0])
                    d_py = self.distance(loc_fk3, loc_ik2)
                    pm.setAttr(loc_fk2.rotate, [0, 0, 90])
                    d_az = self.distance(loc_fk3, loc_ik2)
                    pm.setAttr(loc_fk2.rotate, [0, 0, -90])
                    d_pz = self.distance(loc_fk3, loc_ik2)
                    dict_obj = {'+X': d_ax, '-X': d_px, '+Y': d_ay, '-Y': d_py, '+Z': d_az, '-Z': d_pz}
                    inputValues[10] = min(dict_obj, key=dict_obj.get)
                    pm.delete(loc_fk2, loc_ik2, loc_fk3)
            pm.delete(loc_fk_1, loc_fk_2)
        else:
            pm.warning('Axial acquisition failed !')

        # 骨骼偏移值_FK
        j_offset_fk1 = self.offset_V(inputValues[11][0], inputValues[0])
        j_offset_fk2 = self.offset_V(inputValues[11][1], inputValues[1])
        j_offset_fk3 = self.offset_V(inputValues[11][2], inputValues[2])
        inputValues[12] = [j_offset_fk1, j_offset_fk2, j_offset_fk3]

        # 骨骼偏移值_IK
        j_offset_ik1 = self.offset_V(inputValues[11][2], inputValues[3])
        j_offset_ik2 = self.offset_V(inputValues[11][1], inputValues[4])
        inputValues[13] = [j_offset_ik1, j_offset_ik2]

        return inputValues

    # 自动分类leg,arm,L,R
    def auto_arm_leg(self):
        L_arm = []
        R_arm = []
        L_leg = []
        R_leg = []
        # arm_leg = {'arm': ['Arm', 'arm', 'Blender'], 'leg': ['Leg', 'leg'], 'L': ['_L','L_','_l','l_','_L_','_l_'], 'R': ['_R','R_','_r','r_','_R_','_r_']}
        sel = pm.ls(sl=True)

        joint_data = self.joint_get()
        if joint_data:
            for selCtrl in sel:
                # {'L': {'arm': {'FK1': '', 'FK2': '', 'FK3': ''}, 'leg': {'FK1': '', 'FK2': '', 'FK3': ''}},
                # 'R': {'arm': {'FK1': '', 'FK2': '', 'FK3': ''}, 'leg': {'FK1': '', 'FK2': '', 'FK3': ''}}}

                L_R = list(re.findall(r":(L_).*|^(L_).*|.*(_L)$|.*?(_L_)|:(R_).*|^(R_).*|.*(_R)$|.*?(_R_)", str(selCtrl), re.I))
                if L_R:
                    L_R = list(filter(None, L_R[0]))[0]
                else:
                    L_R = ''
                    pm.displayInfo('No L_R found !')
                if True in [i in str(selCtrl) for i in self.arm_leg['arm']]:
                    if L_R in self.arm_leg['L']:
                        L_arm = self.autoGetInput(selCtrl, 'L', 'arm', list(joint_data['L']['arm'].values()))
                    if L_R in self.arm_leg['R']:
                        R_arm = self.autoGetInput(selCtrl, 'R', 'arm', list(joint_data['R']['arm'].values()))
                if True in [i in str(selCtrl) for i in self.arm_leg['leg']]:
                    if L_R in self.arm_leg['L']:
                        L_leg = self.autoGetInput(selCtrl, 'L', 'leg', list(joint_data['L']['leg'].values()))
                    if L_R in self.arm_leg['R']:
                        R_leg = self.autoGetInput(selCtrl, 'R', 'leg', list(joint_data['R']['leg'].values()))

            return {'L_arm': L_arm, 'R_arm': R_arm, 'L_leg': L_leg, 'R_leg': R_leg}
        else:
            return {'L_arm': [], 'R_arm': [], 'L_leg': [], 'R_leg': []}

    # 获取四肢骨骼========================================================================================================
    def joint_get(self):
        # 获取场景中所有的蒙皮簇节点
        alljointsList = pm.ls(type='joint')
        # skinClusters = pm.ls(type='skinCluster')
        # # 创建一个集合，用于存储参与蒙皮的骨骼，以去除重复项
        # jointsSet = set()
        # # 遍历所有蒙皮簇节点
        # for sc in skinClusters:
        #     # 使用skinCluster的"influence"命令获取当前skinCluster影响的骨骼
        #     influences = pm.skinCluster(sc, query=True, influence=True)
        #     # 将获取到的骨骼添加到集合中
        #     jointsSet.update(influences)
        # # 将集合转换为列表
        # jointsList = list(jointsSet)

        # 过滤
        jointsList_LR_part = {'L': {'arm': {'FK1': '', 'FK2': '', 'FK3': ''}, 'leg': {'FK1': '', 'FK2': '', 'FK3': ''}},
                              'R': {'arm': {'FK1': '', 'FK2': '', 'FK3': ''}, 'leg': {'FK1': '', 'FK2': '', 'FK3': ''}}
                              }
        joints_remove = ['bend', 'twist', 'stretch', 'backPsd', 'lowPsd', 'forwardPsd', 'upPsd', 'slider']
        part_re = []
        for i in alljointsList:
            i = str(i)
            L_R = ''
            part_ = ''
            part_FK = ''
            arm_leg_part = ''

            if True not in [x in i.upper() for x in self.IK_FK]:
                if True not in [x.lower() in i.lower() for x in joints_remove]:
                    L_R_list = list(
                        re.findall(r":(L_).*|^(L_).*|.*(_L)$|.*?(_L_)|:(R_).*|^(R_).*|.*(_R)$|.*?(_R_)", str(i), re.I))
                    if L_R_list:
                        L_R = list(filter(None, L_R_list[0]))[0]

                    if ':' in i:
                        i_ = i.replace(':', '_')
                    else:
                        i_ = i
                    for key in self.CTRL_NAME_INI:
                        for part in self.CTRL_NAME_INI[key]:
                            if part != 'IK1' and part != 'IK2':
                                if True in [x.upper() in [(i_.split('_')[y_i-1] + '_' + y).upper() if y.isdigit() else y.upper() for y_i, y in enumerate(i_.split('_'))] for x in
                                            self.CTRL_NAME_INI[key][part]]:
                                    if (key + '_' + part + '_' + L_R) in part_re:
                                        if part == 'FK1':
                                            if True in [x.upper() in [y.upper() for y in i_.split('_')] for x in self.CTRL_NAME_INI[key][part][0:1]]:
                                                arm_leg_part = part
                                                part_ = key
                                                part_FK = part
                                        if part == 'FK2':
                                            if True in [x.upper() in [y.upper() for y in i_.split('_')] for x in self.CTRL_NAME_INI[key][part][0:1]]:
                                                arm_leg_part = part
                                                part_ = key
                                                part_FK = part
                                        if part == 'FK3':
                                            if True in [x.upper() in [y.upper() for y in i_.split('_')] for x in self.CTRL_NAME_INI[key][part][0:1]]:
                                                arm_leg_part = part
                                                part_ = key
                                                part_FK = part
                                        if len(i) < len(jointsList_LR_part[[i for i in L_R.split('_') if i][0].upper()][key][part]):
                                            if not False in [ii in jointsList_LR_part[[i for i in L_R.split('_') if i][0].upper()][key][part].split('_') for ii in i.split('_')]:
                                                arm_leg_part = part
                                                part_ = key
                                                part_FK = part
                                    if (key + '_' + part + '_' + L_R) not in part_re:
                                        part_re.append(key + '_' + part + '_' + L_R)
                                        arm_leg_part = part
                                        part_ = key
                                        part_FK = part
                                        # print('joint::::::::::', key + '_' + part + '_' + L_R, '===========', i)

                    if arm_leg_part:
                        if 'L' in L_R.upper():
                            for part in jointsList_LR_part['L']:
                                for FK_part in jointsList_LR_part['L'][part]:
                                    if part == part_ and FK_part == part_FK:
                                        jointsList_LR_part['L'][part][FK_part] = i
                        elif 'R' in L_R.upper():
                            for part in jointsList_LR_part['R']:
                                for FK_part in jointsList_LR_part['R'][part]:
                                    if part == part_ and FK_part == part_FK:
                                        jointsList_LR_part['R'][part][FK_part] = i
        NO_FOUND = 0
        for key in jointsList_LR_part:
            for part in jointsList_LR_part[key]:
                for FK_part in jointsList_LR_part[key][part]:
                    if not jointsList_LR_part[key][part][FK_part]:
                        NO_FOUND = 1
                        pm.displayInfo('No joints found: {} !'.format(key + '_' + part + '_' + FK_part))
        if NO_FOUND:
            return {}
        else:
            return jointsList_LR_part

    # 警告弹框
    @staticmethod
    def popupWarning(message, title='Input Error'):

        result = pm.confirmDialog(
            title=title,
            message=message,
            button=['OK'],
            defaultButton='OK', )

        return result

    # 保存数据=======================================
    # {'L_arm': L_arm, 'R_arm': R_arm, 'L_leg': L_leg, 'R_leg': R_leg}
    def save_data(self):
        # get spacename
        sel = pm.ls(sl=True)
        if sel:
            spacename = sel[0].split(':')[0] if len(sel[0].split(':')) >= 2 else 'SpaceNameNull'
        # get attr
        attr = pm.channelBox("mainChannelBox", query=True, selectedMainAttributes=True)
        if attr is not None:
            get_data = self.auto_arm_leg()
            if not (get_data['L_arm'] == ['NO Ctrl Found'] or get_data['R_arm'] == ['NO Ctrl Found'] or get_data['L_leg'] == ['NO Ctrl Found'] or get_data['R_leg'] == ['NO Ctrl Found']):
                if not pm.objExists(spacename + '_AUTO_IK_FK_NETWORK'):
                    pm.createNode('network', n=spacename + '_AUTO_IK_FK_NETWORK')
                    if not pm.objExists(spacename + '_AUTO_IK_FK_NETWORK.notes'):
                        pm.addAttr(spacename + '_AUTO_IK_FK_NETWORK', type='string', ln='notes')
                    pm.setAttr(spacename + '_AUTO_IK_FK_NETWORK.notes', str(get_data), type='string')
                    pm.displayInfo('Successfully Match !')
                else:
                    if pm.objExists(spacename + '_AUTO_IK_FK_NETWORK.notes'):
                        ik_fk_exist_data = self.take_data(selected=sel)
                        if ik_fk_exist_data:
                            for item in ik_fk_exist_data:
                                if item == 'L_arm':
                                    if get_data['L_arm']:
                                        ik_fk_exist_data[item] = get_data['L_arm']
                                if item == 'R_arm':
                                    if get_data['R_arm']:
                                        ik_fk_exist_data[item] = get_data['R_arm']
                                if item == 'L_leg':
                                    if get_data['L_leg']:
                                        ik_fk_exist_data[item] = get_data['L_leg']
                                if item == 'R_leg':
                                    if get_data['R_leg']:
                                        ik_fk_exist_data[item] = get_data['R_leg']
                            pm.setAttr(spacename + '_AUTO_IK_FK_NETWORK.notes', str(ik_fk_exist_data), type='string')
                            pm.displayInfo('Successfully Match !')
                        else:
                            pm.setAttr(spacename + '_AUTO_IK_FK_NETWORK.notes', str(get_data), type='string')
                            pm.displayInfo('Successfully Match !')
            else:
                pm.warning('Failed Match !')
        pm.select(sel)
        self.color_text()

    # 读取数据=======================================
    def take_data(self, selected, data_type='dict'):
        if ':' in selected[0]:
            spaceName = selected[0].split(':')[0]
        else:
            spaceName = 'SpaceNameNull'
        if pm.objExists(spaceName + '_AUTO_IK_FK_NETWORK.notes'):
            ik_fk_str = pm.getAttr(spaceName + '_AUTO_IK_FK_NETWORK.notes')
            if ik_fk_str:
                ik_fk_data = dict(eval(ik_fk_str))
                if data_type == 'list':
                    if ik_fk_data:
                        for key in ik_fk_data:
                            if True in [i == selected[0] for i in ik_fk_data[key]]:
                                L_R_arm_leg = ik_fk_data[key]
                                return L_R_arm_leg
                else:
                    return ik_fk_data
            else:
                pm.warning('No Data! Please Match First!')
        else:
            pm.warning('No Data! Please Match First!')

    # 匹配IK_FK自动化=====================================================================================================
    # {'L_arm': L_arm, 'R_arm': R_arm, 'L_leg': L_leg, 'R_leg': R_leg}
    def matchIkFk_Auto(self, to_fk=1, auto=True, mode='jointMode'):
        auto_fk = to_fk
        sel = pm.ls(sl=True)
        L_R_arm_leg = []
        side = ''
        limb = ''
        if sel:
            ik_fk_data = self.take_data(selected=sel)
            if ik_fk_data:
                for key in ik_fk_data:
                     for index, i in enumerate(ik_fk_data[key]):
                         if i == sel[0]:
                            L_R_arm_leg = ik_fk_data[key]
                            side = key.split('_')[0]
                            limb = key.split('_')[1]
                            if auto:
                                # 选fk转ik
                                if index in [0, 1, 2]:
                                    auto_fk = 0
                                # 选ik转fk
                                elif index in [3, 4]:
                                    auto_fk = 1
                                #
                                elif index == 5:
                                    if L_R_arm_leg[7] == 1:
                                        if pm.getAttr(L_R_arm_leg[6]) == 0:
                                            auto_fk = 0
                                    else:
                                        if pm.getAttr(L_R_arm_leg[6]) == 0:
                                            auto_fk = 1

                if L_R_arm_leg:
                    if L_R_arm_leg[0]:
                        fkshldr, fkellbow, fkwrist, ikwrist, ikpv, switchCtrl, switchAttr, switch0isfk, switchAttrRange, rotOffset, bendKneeAxis, joint, joint_offset, joint_offset_IK = L_R_arm_leg
                else:
                    pm.warning('No Data! Please AUTO Match First!')
                    return

                if auto_fk == 1:
                    if L_R_arm_leg[7] == 1:
                        if not pm.getAttr(L_R_arm_leg[6]) == 0:
                            if mode == 'jointMode':
                                # (FK1, FK2, FK3, switchCtrl, switchAttr, switch0isfk=1, switchAttrRange=1, joint_list = ['fk1', 'fk2', 'fk3'], joint_offset = [], f2_rotateAxis)
                                ikfkMatch_jointMode(fkshldr, fkellbow, fkwrist, switchCtrl, switchAttr, switch0isfk, switchAttrRange, joint, joint_offset, bendKneeAxis)
                            else:
                                ikfkMatch(fkwrist, fkellbow, fkshldr, ikwrist, ikpv, switchCtrl, switchAttr.split('.')[1], switch0isfk=switch0isfk,
                                          switchAttrRange=switchAttrRange, rotOffset=rotOffset, side=side,
                                          limb=limb, bendKneeAxis=bendKneeAxis)
                    else:
                        if not pm.getAttr(L_R_arm_leg[6]) == L_R_arm_leg[8]:
                            if mode == 'jointMode':
                                ikfkMatch_jointMode(fkshldr, fkellbow, fkwrist, switchCtrl, switchAttr, switch0isfk,
                                          switchAttrRange, joint, joint_offset, bendKneeAxis)
                            else:
                                ikfkMatch(fkwrist, fkellbow, fkshldr, ikwrist, ikpv, switchCtrl, switchAttr.split('.')[1], switch0isfk=switch0isfk,
                                      switchAttrRange=switchAttrRange, rotOffset=rotOffset, side=side,
                                      limb=limb, bendKneeAxis=bendKneeAxis)

                elif auto_fk == 0:
                    if L_R_arm_leg[7] == 1:
                        if not pm.getAttr(L_R_arm_leg[6]) == L_R_arm_leg[8]:
                            if mode == 'jointMode':
                                fkikMatch_jointMode(ikwrist, ikpv, switchCtrl, switchAttr, switch0isfk, switchAttrRange,
                                                    joint, joint_offset_IK)
                            else:
                                start_IK = time.time()
                                fkikMatch(fkwrist, fkellbow, fkshldr, ikwrist, ikpv, switchCtrl, switchAttr.split('.')[1], switch0isfk=switch0isfk,
                                          switchAttrRange=switchAttrRange, rotOffset=rotOffset, side=side,
                                          limb=limb)
                    else:
                        if not pm.getAttr(L_R_arm_leg[6]) == 0:
                            if mode == 'jointMode':
                                fkikMatch_jointMode(ikwrist, ikpv, switchCtrl, switchAttr, switch0isfk, switchAttrRange,
                                                    joint, joint_offset_IK)
                            else:
                                fkikMatch(fkwrist, fkellbow, fkshldr, ikwrist, ikpv, switchCtrl, switchAttr.split('.')[1], switch0isfk=switch0isfk,
                                      switchAttrRange=switchAttrRange, rotOffset=rotOffset, side=side,
                                      limb=limb)

                pm.select(switchCtrl)
            else:
                pm.warning('No Data! Please AUTO Match First!')

    # ik_fk转换==========================================================================================================
    # FK1,FK2,FK3,IK Ctrl,IK Pole,switchCtrl, switchAttr,switch0isfk, switchAttrRange, rotOffset, bendKneeAxis
    def switch_ik_fk(self, fk=True, auto=False):
        sel = pm.ls(sl=True)
        L_R_arm_leg = []
        if sel:
            ik_fk_data = self.take_data(selected=sel)
            if ik_fk_data:
                for key in ik_fk_data:
                    for index, i in enumerate(ik_fk_data[key]):
                        if i == sel[0]:
                            L_R_arm_leg = ik_fk_data[key]
                            if auto:
                                if pm.getAttr(L_R_arm_leg[6]) == 0:
                                    if L_R_arm_leg[7] == 1:
                                        fk = False
                                    else:
                                        fk = True
                                elif pm.getAttr(L_R_arm_leg[6]) == L_R_arm_leg[8]:
                                    if L_R_arm_leg[7] == 1:
                                        fk = True
                                    else:
                                        fk = False

                            if L_R_arm_leg[7] == 1:
                                if fk:
                                    pm.setAttr(L_R_arm_leg[6], 0)
                                    pm.select(L_R_arm_leg[0:3])
                                else:
                                    pm.setAttr(L_R_arm_leg[6], L_R_arm_leg[8])
                                    pm.select(L_R_arm_leg[3:5])
                            else:
                                if fk:
                                    pm.setAttr(L_R_arm_leg[6], L_R_arm_leg[8])
                                    pm.select(L_R_arm_leg[0:3])
                                else:
                                    pm.setAttr(L_R_arm_leg[6], 0)
                                    pm.select(L_R_arm_leg[3:5])
                if not L_R_arm_leg:
                    pm.warning('No Data! Please AUTO Match First!')
            else:
                pm.warning('No Data! Please AUTO Match First!')

    # 选择ik fk==========================================================================================================
    def select_All(self, mode='fk'):
        sel = pm.ls(sl=True)
        L_R_arm_leg = []
        if sel:
            ik_fk_data = self.take_data(selected=sel)
            if ik_fk_data:
                for key in ik_fk_data:
                    if True in [i == sel[0] for i in ik_fk_data[key]]:
                        L_R_arm_leg = ik_fk_data[key]
                        if mode == 'fk':
                            pm.select(L_R_arm_leg[0:3])
                        elif mode == 'ik':
                            pm.select(L_R_arm_leg[3:5])
                        else:
                            pm.select(L_R_arm_leg[0:6])
                if not L_R_arm_leg:
                    pm.warning('No Data! Please AUTO Match First!')
            else:
                pm.warning('No Data! Please AUTO Match First!')

    # 批量转换IK_FK======================================================================================================
    def batch_IK_FK(self, ik=True, mode='jointMode'):
        global gMainProgressBar
        pm.progressBar(gMainProgressBar,
                       edit=True,
                       beginProgress=True,
                       isInterruptable=True,
                       status='Batch Calculation ...')

        sel = pm.ls(sl=True)
        time_range = pm.mel.eval('global string $gPlayBackSlider; timeControl -ra -q $gPlayBackSlider;')
        if sel:
            data_list = self.take_data(selected=sel, data_type='list')
            frames = pm.keyframe(sel, query=True, timeChange=True)
            frames = (list(dict.fromkeys(frames)))
            frames.sort()

            startTime = time.time()
            if time_range[1] - time_range[0] > 1:
                pm.progressBar(gMainProgressBar, edit=True, max=len([i for i in frames if time_range[0] <= i <= time_range[1]]))
                for frame in frames:
                    if time_range[0] <= frame <= time_range[1]:
                        pm.currentTime(frame)
                        pm.setKeyframe(data_list[5])
                for frame in frames:
                    if not pm.progressBar(gMainProgressBar, query=True, isCancelled=True):
                        if time_range[0] <= frame <= time_range[1]:
                            if ik:
                                pm.currentTime(frame)
                                if mode == 'jointMode':
                                    self.matchIkFk_Auto(to_fk=0, auto=False, mode='jointMode')
                                elif mode == 'ctrlMode':
                                    self.matchIkFk_Auto(to_fk=0, auto=False, mode='ctrlMode')
                            else:
                                pm.currentTime(frame)
                                if mode == 'jointMode':
                                    self.matchIkFk_Auto(to_fk=1, auto=False, mode='jointMode')
                                elif mode == 'ctrlMode':
                                    self.matchIkFk_Auto(to_fk=1, auto=False, mode='ctrlMode')
                            pm.progressBar(gMainProgressBar, edit=True, step=1)
                    else:
                        break

            else:
                min = pm.playbackOptions(query=True, min=True)
                max = pm.playbackOptions(query=True, max=True)
                pm.progressBar(gMainProgressBar, edit=True, max=len([i for i in frames if min <= i <= max]))
                for frame in frames:
                    if min <= frame <= max:
                        pm.currentTime(frame)
                        pm.setKeyframe(data_list[5])
                for frame in frames:
                    if not pm.progressBar(gMainProgressBar, query=True, isCancelled=True):
                        if min <= frame <= max:
                            if ik:
                                pm.currentTime(frame)
                                if mode == 'jointMode':
                                    self.matchIkFk_Auto(to_fk=0, auto=False, mode='jointMode')
                                elif mode == 'ctrlMode':
                                    self.matchIkFk_Auto(to_fk=0, auto=False, mode='ctrlMode')
                            else:
                                pm.currentTime(frame)
                                if mode == 'jointMode':
                                    self.matchIkFk_Auto(to_fk=1, auto=False, mode='jointMode')
                                elif mode == 'ctrlMode':
                                    self.matchIkFk_Auto(to_fk=1, auto=False, mode='ctrlMode')
                            pm.progressBar(gMainProgressBar, edit=True, step=1)
                    else:
                        break

            pm.progressBar(gMainProgressBar, edit=True, endProgress=True)
            minutes, sec = divmod(int(time.time() - startTime), 60)
            pm.displayInfo('Total time: {}min {}s'.format(minutes, sec))

# IK对齐FK,转成IK
def fkikMatch(fkwrist, fkellbow, fkshldr, ikwrist, ikpv, switchCtrl, switchAttr, switch0isfk=1, switchAttrRange=1,
              rotOffset=[0, 0, 0], side='R', limb='arm'):
    '''
    Match fk to ik. Recreate the ik chain
    Args:
        fkwrist:
        fkellbow:
        fkshldr:
        ikwrist:
        ikpv:
        switchCtrl:
        switchAttr:
        switch0isfk:
        rotOffset:

    Returns:

    '''
    switch = '%s.%s' % (switchCtrl, switchAttr)

    if pm.objExists('snapGrp'): pm.delete('snapGrp')
    snapGrp = pm.createNode('transform', name='snapGrp')
    clist = []

    # dup controls to constrain
    fk_wristDup = pm.duplicate(fkwrist, parentOnly=1, n='fk_wristDup')[0]
    unlockAttributes([fk_wristDup])
    pm.parent(fk_wristDup, snapGrp)

    # go to fk mode to match correct position
    if switch0isfk == 0:
        pm.setAttr(switch, switchAttrRange)  # 0 is fk
    else:
        pm.setAttr(switch, 0)

    # store fk keyframes on attribute or not:
    fkwrist_key, fkellbow_key, fkshldr_key = pm.keyframe(fkwrist, q=1, t=pm.currentTime()), \
        pm.keyframe(fkellbow, q=1, t=pm.currentTime()), \
        pm.keyframe(fkshldr, q=1, t=pm.currentTime())

    # get positions from fk
    fkwRaw = pm.xform(fkwrist, ws=1, q=1, t=1)
    fkwPos = om.MVector(fkwRaw[0], fkwRaw[1], fkwRaw[2])
    fkeRaw = pm.xform(fkellbow, ws=1, q=1, t=1)
    fkePos = om.MVector(fkeRaw[0], fkeRaw[1], fkeRaw[2])
    fksRaw = pm.xform(fkshldr, ws=1, q=1, t=1)
    fksPos = om.MVector(fksRaw[0], fksRaw[1], fksRaw[2])

    # store rotation
    fkwRotRaw = pm.xform(fkwrist, q=1, ro=1)
    fkeRotRaw = pm.xform(fkellbow, q=1, ro=1)
    fksRotRaw = pm.xform(fkshldr, q=1, ro=1)

    # zero out fk
    pm.xform(fkshldr, ro=(0, 0, 0))
    pm.xform(fkellbow, ro=(0, 0, 0))
    pm.xform(fkwrist, ro=(0, 0, 0))
    snap(fkwrist, fk_wristDup)

    # create orig ik wrist dup to get offset
    pm.xform(ikwrist, ro=(0, 0, 0))
    ik_wristDup = pm.duplicate(ikwrist, parentOnly=1, n='ik_wristDup')[0]
    unlockAttributes([ik_wristDup])
    pm.parent(ik_wristDup, fk_wristDup)
    snap(fk_wristDup, ik_wristDup, pos=1, rot=1)
    # snap(ikwrist, ik_wristDup, pos=0, rot=1)

    ik_wristDupOffset = pm.duplicate(ik_wristDup, parentOnly=1, n='ik_wristDup_offset')[0]
    pm.parent(ik_wristDupOffset, ik_wristDup)

    clist.append(pm.parentConstraint(fkwrist, fk_wristDup, mo=0))

    # restore fk
    pm.xform(fkshldr, ro=fksRotRaw)
    pm.xform(fkellbow, ro=fkeRotRaw)
    pm.xform(fkwrist, ro=fkwRotRaw)

    # considering rotation offset
    pm.setAttr('%s.rx' % ik_wristDupOffset, rotOffset[0])
    pm.setAttr('%s.ry' % ik_wristDupOffset, rotOffset[1])
    pm.setAttr('%s.rz' % ik_wristDupOffset, rotOffset[2])

    # pole vector
    pvLoc = poleVectorPosition(fkshldr, fkellbow, fkwrist, length=12, createLoc=1)
    pm.parent(pvLoc, snapGrp)

    # snap ik
    for ctrl in [ikwrist, ikpv]:
        if len(pm.keyframe(ctrl, q=1)) > 0:
            pm.cutKey(ctrl, t=pm.currentTime())

    snap(ik_wristDupOffset, ikwrist)
    snap(pvLoc, ikpv, pos=1, rot=0)

    for ctrl in [ikwrist, ikpv]:
        # if len(pm.keyframe(ctrl, q=1)) > 0:
            pm.setKeyframe(ctrl, t=pm.currentTime(), s=0)

    if debug == True:
        clist.append(pm.parentConstraint(ik_wristDupOffset, ikwrist))

    # clean up
    if debug == False:
        pm.delete(clist)
        pm.delete(snapGrp)

    # pm.delete(pvLoc)
    # if not debug: pm.delete(fkRotLocWs)

    # clean up eventually created keyframe on fk ctrl on switch frame
    if len(fkwrist_key) == 0:
        try:
            pm.cutKey(fkwrist, t=pm.currentTime())
        except:
            pass
    if len(fkellbow_key) == 0:
        try:
            pm.cutKey(fkellbow, t=pm.currentTime())
        except:
            pass
    if len(fkshldr_key) == 0:
        try:
            pm.cutKey(fkshldr, t=pm.currentTime())
        except:
            pass

    # go to ik mode
    if switch0isfk == 0:
        pm.setAttr(switch, 0)
    else:
        pm.setAttr(switch, switchAttrRange)

    pm.dgdirty([ikwrist, ikpv])
    pm.dgdirty([fkwrist, fkellbow, fkshldr])

    _logger.info('Done matching FK to IK.')


# IK对齐FK,转成IK-Joint模式===============================================================================================
# 求a对于b的偏移值
def offsetValue(a, b):
    loc_a = loc_create_world(a)
    pm.parent(loc_a, b)
    offset_V_r = pm.getAttr(loc_a + '.rotate')
    pm.setAttr(loc_a + '.translate', [0, 0, 0])
    pm.parent(loc_a, a)
    target_V_t = pm.getAttr(loc_a + '.translate')
    pm.delete(loc_a)
    return target_V_t, offset_V_r


def fkikMatch_jointMode(IK1, IK2, switchCtrl, switchAttr, switch0isfk=1, switchAttrRange=1,
                        joint_list = ['fk1', 'fk2', 'fk3'], joint_offset_IK = []):
    loc_ik1 = loc_create_world(joint_list[2])
    pm.parent(loc_ik1, joint_list[2])
    pm.setAttr(loc_ik1 + '.translate', joint_offset_IK[0][0:3])
    pm.setAttr(loc_ik1 + '.rotate', joint_offset_IK[0][3:6])
    pm.parent(loc_ik1, world=True)

    loc_ik2 = loc_create_world(joint_list[1])
    pm.parent(loc_ik2, joint_list[1])
    pm.setAttr(loc_ik2 + '.translate', joint_offset_IK[1][0:3])
    pm.setAttr(loc_ik2 + '.rotate', joint_offset_IK[1][3:6])
    pm.parent(loc_ik2, world=True)

    # target_ik1_t, offset_ik1_r = offsetValue(IK1, loc_ik1)
    #
    # pm.move(IK1, target_ik1_t, r=True, ls=True, wd=True)
    # pm.rotate(IK1, [0 - i for i in offset_ik1_r], r=True, os=True)

    pm.parentConstraint([loc_ik1, IK1])
    pm.pointConstraint([loc_ik2, IK2])
    pm.setKeyframe([IK1, IK2, switchCtrl], t=pm.currentTime(), s=0)

    pm.delete([loc_ik1, loc_ik2])
    if switch0isfk == 1:
        pm.setAttr(switchAttr, switchAttrRange)
    else:
        pm.setAttr(switchAttr, 0)


# FK对齐IK,转成FK
def ikfkMatch(fkwrist, fkellbow, fkshldr, ikwrist, ikpv, switchCtrl, switchAttr, switch0isfk=1, switchAttrRange=1,
              rotOffset=[0, 0, 0], side='R', limb='arm', guessUp=1, bendKneeAxis='+X'):
    '''
    Snap fk to ik controls by building ik joint form fk control position and lining up to ik
    Args:
    Returns:

    '''
    ns = fkwrist.split(':')[0]
    switch = '%s.%s' % (switchCtrl, switchAttr)
    clist = []

    if pm.objExists('snapGrp'): pm.delete('snapGrp')
    snapGrp = pm.createNode('transform', name='snapGrp')

    # store if keyframe on ik attribute or not:
    ikwrist_key, ikpv_key = pm.keyframe(ikwrist, q=1, t=pm.currentTime()), \
        pm.keyframe(ikpv, q=1, t=pm.currentTime())

    _logger.info('matching. switch attr range is %s' % switchAttrRange)
    # go to fk mode to match correct position (some riggs use same foot ctrl for ik and fk)
    if switch0isfk == 0:
        pm.setAttr(switch, switchAttrRange)  # 0 is fk
    else:
        pm.setAttr(switch, 0)

    # zero out fk
    pm.xform(fkshldr, ro=(0, 0, 0))
    pm.xform(fkellbow, ro=(0, 0, 0))
    pm.xform(fkwrist, ro=(0, 0, 0))

    try:
        pm.xform(fkshldr, t=(0, 0, 0))
    except:
        pass
    try:
        pm.xform(fkellbow, t=(0, 0, 0))
    except:
        pass
    try:
        pm.xform(fkwrist, t=(0, 0, 0))
    except:
        pass

    _logger.info('root loc')
    pm.dgdirty([fkshldr, fkellbow, fkwrist])
    root_loc = pm.group(empty=1, n='fk_shld_root')
    pm.parent(root_loc, snapGrp)
    snap(fkshldr, root_loc)

    fkshldr_dup = pm.duplicate(fkshldr, parentOnly=1)[0]
    fkellbow_dup = pm.duplicate(fkellbow, parentOnly=1)[0]
    fkwrist_dup = pm.duplicate(fkwrist, parentOnly=1)[0]

    # unlock all of duplicate A's arrtibutes
    basicTransforms = ['translateX', 'translateY', 'translateZ', 'translate', 'rotateX', '  rotateY', 'rotateZ',
                       'rotate']
    for attr in basicTransforms:
        # unlock attr
        pm.setAttr((fkshldr_dup + '.' + attr), lock=False, k=True)
        pm.setAttr((fkellbow_dup + '.' + attr), lock=False, k=True)
        pm.setAttr((fkwrist_dup + '.' + attr), lock=False, k=True)
        pm.select([fkshldr_dup, fkellbow_dup, fkwrist_dup])
        _logger.info('line up fk duplicates to fk controlssss %s %s %s' % (fkshldr_dup, fkellbow_dup, fkwrist_dup))

    # line up fk duplicates to fk controls
    pm.parent(fkshldr_dup, snapGrp)
    snap(fkshldr, fkshldr_dup, pos=1, rot=1)
    pm.parent(fkellbow_dup, fkshldr_dup)
    snap(fkellbow, fkellbow_dup, pos=1, rot=1)
    pm.parent(fkwrist_dup, fkellbow_dup)
    snap(fkwrist, fkwrist_dup, pos=1, rot=1)

    pm.select(snapGrp)
    _logger.info('snapping fk shoulder to ik')

    root_ikSnap = pm.joint(n='root_ikSnap', p=pm.xform(fkshldr, t=1, q=1, ws=1), orientation=(0, 0, 0))
    pm.parent(root_ikSnap, root_loc)
    snap(fkshldr, root_ikSnap, rot=1, pos=1)
    ikshldr_jnt = pm.joint(n='ikshldr_jnt', p=pm.xform(fkshldr, t=1, q=1, ws=1), orientation=(0, 0, 0))
    snap(fkellbow, ikshldr_jnt, rot=1, pos=0)
    try:
        snap(fkshldr, ikshldr_jnt, rot=0, pos=1)
    except:
        pass
    _logger.info('snapping fk ellbow to ik')
    ikellbow_jnt = pm.joint(n='ikellbow_jnt', p=pm.xform(fkellbow, t=1, q=1, ws=1), orientation=(0, 0, 0))
    snap(fkellbow, ikellbow_jnt, rot=1, pos=0)
    try:
        snap(fkellbow, ikellbow_jnt, rot=0, pos=1)
    except:
        pass
    _logger.info('snapping fk wrist to ik')
    ikwrist_jnt = pm.joint(n='ikwrist_jnt', p=pm.xform(fkwrist, t=1, q=1, ws=1), orientation=(0, 0, 0))
    snap(fkellbow, ikwrist_jnt, rot=1, pos=0)
    try:
        snap(fkwrist, ikwrist_jnt, rot=0, pos=1)
    except:
        pass
    # aimaxis = max(pm.getAttr('%s.tx'%ikellbow_jnt), pm.getAttr('%s.tx'%ikellbow_jnt), pm.getAttr('%s.tx'%ikellbow_jnt))
    _logger.info('freeze transform')
    pm.makeIdentity(ikshldr_jnt, apply=1)
    pm.makeIdentity(ikellbow_jnt, apply=1)
    pm.makeIdentity(ikwrist_jnt, apply=1)

    multiplyer = 1
    if bendKneeAxis[0] == '-':
        mutliplyer = -1
    if abs(pm.getAttr('%s.jointOrient%s' % (ikellbow_jnt, bendKneeAxis[1]))) < 0.1:
        pm.warning('Warning small joint orient. Setting Prefferec Angle to Y ')
        pm.setAttr('%s.preferredAngle%s' % (ikellbow_jnt, bendKneeAxis[1]), 12.0 * multiplyer)
        pm.setAttr('%s.jointOrient%s' % (ikellbow_jnt, bendKneeAxis[1]), 0.01 * multiplyer)

    # pole vector
    pole_ikSnap = pm.spaceLocator(n='pole_ikSnap')
    pm.parent(pole_ikSnap, fkellbow_dup)

    _logger.info('snap pole ik to fkellbow knee bend axis is %s' % bendKneeAxis)
    # temp pole vector position. use the ellbow could use poleVectorPos as well
    snap(fkellbow_dup, pole_ikSnap)

    _logger.info('considering kneebendaxis. %s' % bendKneeAxis)
    reverse = 1
    if side == 'L': reverse = -1

    if bendKneeAxis == '-X':
        pole_ikSnap.tz.set(pole_ikSnap.tz.get() + 0.5 * reverse)
    elif bendKneeAxis == '+X':
        pole_ikSnap.tz.set(pole_ikSnap.tz.get() - 0.5 * reverse)
    elif bendKneeAxis == '-Y':
        pole_ikSnap.tz.set(pole_ikSnap.tz.get() + 0.5 * reverse)
    elif bendKneeAxis == '+Y':
        pole_ikSnap.tz.set(pole_ikSnap.tz.get() - 0.5 * reverse)
    elif bendKneeAxis == '-Z':
        pole_ikSnap.ty.set(pole_ikSnap.ty.get() - 0.5 * reverse)
    elif bendKneeAxis == '+Z':
        pole_ikSnap.ty.set(pole_ikSnap.ty.get() + 0.5 * reverse)

    pm.parent(pole_ikSnap, snapGrp)

    # ik handle
    ikHandle_ikSnap = pm.ikHandle(sj=ikshldr_jnt, ee=ikwrist_jnt, sol='ikRPsolver')
    pm.parent(ikHandle_ikSnap[0], snapGrp)

    pm.poleVectorConstraint(pole_ikSnap, ikHandle_ikSnap[0])
    _logger.info('done polevector constraint')

    # wrist offset locator line up to zero out ikwrist
    ikrot = pm.xform(ikwrist, q=1, ro=1)
    pm.xform(ikwrist, ro=(0, 0, 0))
    ikwrist_loc = pm.spaceLocator(n='ikwrist_loc')
    pm.setAttr('%s.rotateOrder' % ikwrist_loc, pm.getAttr('%s.rotateOrder' % ikwrist))
    pm.parent(ikwrist_loc, fkwrist_dup)
    snap(fkwrist, ikwrist_loc, rot=0, pos=1)
    snap(fkwrist, ikwrist_loc, rot=1, pos=0)

    ikwrist_loc_offset = pm.spaceLocator(n='ikwrist_loc_offset')
    pm.setAttr('%s.rotateOrder' % ikwrist_loc_offset, pm.getAttr('%s.rotateOrder' % ikwrist))
    pm.parent(ikwrist_loc_offset, ikwrist_loc)
    snap(ikwrist_jnt, ikwrist_loc_offset, rot=0, pos=1)
    snap(fkwrist, ikwrist_loc_offset, rot=1, pos=0)

    # considering rotation offset (reverse)
    _logger.info('considering rotation offset')
    fkwrist_rotOrder = pm.getAttr('%s.rotateOrder' % fkwrist)
    ikwrist_rotOrder = pm.getAttr('%s.rotateOrder' % ikwrist)
    _logger.debug('rotation order ikwrist: %s. fkwrist: %s' % (fkwrist_rotOrder, ikwrist_rotOrder))
    pm.setAttr('%s.rx' % ikwrist_loc_offset, rotOffset[0])
    pm.setAttr('%s.ry' % ikwrist_loc_offset, rotOffset[1])
    pm.setAttr('%s.rz' % ikwrist_loc_offset, rotOffset[2])

    # constrain fk ctrl dups to ikSnap locs
    _logger.info('constrain fk ctrl dups to ikSnap locs')
    clist.append(pm.parentConstraint(ikshldr_jnt, fkshldr_dup, skipTranslate=['x', 'y', 'z'], mo=1))
    clist.append(pm.parentConstraint(ikellbow_jnt, fkellbow_dup, skipTranslate=['x', 'y', 'z'], mo=1))
    clist.append(pm.parentConstraint(ikwrist_jnt, fkwrist_dup, mo=1))

    fkwrist_loc = pm.spaceLocator(n='fkwrist_loc')
    pm.setAttr('%s.rotateOrder' % fkwrist_loc, pm.getAttr('%s.rotateOrder' % fkwrist))
    pm.parent(fkwrist_loc, ikwrist_loc_offset)
    snap(fkwrist, fkwrist_loc)
    pm.setAttr('%s.rx' % ikwrist_loc_offset, 0)
    pm.setAttr('%s.ry' % ikwrist_loc_offset, 0)
    pm.setAttr('%s.rz' % ikwrist_loc_offset, 0)

    # rotate back ik
    _logger.info('rotate back ik')
    pm.xform(ikwrist, ro=ikrot)
    clist.append(pm.parentConstraint(ikwrist, ikwrist_loc, mo=0))

    if debugZero:
        return

    # switch to ik mode (some riggs use same foot ctrl for ik and fk)
    if switch0isfk == 0:
        pm.setAttr(switch, 0)  # 0 is fk
    else:
        pm.setAttr(switch, switchAttrRange)

    # line up to ik wrist and pole
    _logger.info('line up to ik wrist and pole')
    clist.append(pm.pointConstraint(ikwrist, ikHandle_ikSnap[0]))
    snap(ikpv, pole_ikSnap, rot=0, pos=1)

    # get wrist rotation
    # snap(ikwrist, fkwrist_loc, rot=1, pos=0)
    # snap(fkshldr_loc, fkshldr, rot=1, pos=0)
    # snap(fkellbow_loc, fkellbow, rot=1, pos=0)
    # snap(fkwrist_loc, fkwrist,  rot=1, pos=0)
    _logger.debug('snapping back to original fk')
    # snap back to original fk ctlrs
    for ctrl in [fkshldr, fkellbow, fkwrist]:
        if len(pm.keyframe(ctrl, q=1)) > 0:
            pm.cutKey(ctrl, t=pm.currentTime())

    _logger.info('snap fk shoulder')
    snap(fkshldr_dup, fkshldr, rot=1, pos=0)
    try:
        snap(fkshldr_dup, fkshldr, pos=1)
    except:
        pass
    _logger.info('snap fk ellbow')
    snap(fkellbow_dup, fkellbow, rot=1, pos=0)
    try:
        snap(fkellbow_dup, fkellbow, pos=1)
    except:
        pass
    _logger.info('snap fk wrist')
    snap(fkwrist_loc, fkwrist, rot=1, pos=0)
    try:
        snap(fkwrist_loc, fkwrist, pos=1)
    except:
        pass

    for ctrl in [fkshldr, fkellbow, fkwrist]:
        # if len(pm.keyframe(ctrl, q=1)) > 0:
            pm.setKeyframe(ctrl, t=pm.currentTime(), s=0)

    pm.dgdirty([fkshldr, fkellbow, fkwrist])

    # debug mode
    if debug == True:
        pm.parentConstraint(fkwrist_loc, fkwrist, mo=0, st=('x', 'y', 'z'))

    # clean up
    if debug == False:
        pm.delete(clist)
        pm.delete(snapGrp)

    # clean up eventually created keyframe on ik ctrl on switch frame
    if len(ikwrist_key) == 0:
        try:
            pm.cutKey(ikwrist, t=pm.currentTime())
        except:
            pass
    if len(ikpv_key) == 0:
        try:
            pm.cutKey(ikpv, t=pm.currentTime())
        except:
            pass

    # set to ik
    if switch0isfk == 0:
        pm.setAttr(switch, switchAttrRange)
    else:
        pm.setAttr(switch, 0)


# FK对齐IK,转成FK-Joint模式===============================================================================================
# b对齐a
def align_obj_world(a, b):
    temp_con = pm.orientConstraint([a, b], mo=False)
    pm.setKeyframe(b)
    pm.delete(temp_con)


# 创建Loc在对象的位置
def loc_create_world(obj):
    loc = pm.spaceLocator(n=obj+'_loc_AT')
    con = pm.parentConstraint([obj, loc])
    pm.delete(con)
    return loc


# 求扭转轴向
def twist_axial(obj1, obj2):
    loc1 = loc_create_world(obj1)
    loc2 = loc_create_world(obj2)
    pm.parent([loc2, loc1])
    t = pm.getAttr(loc2+'.translate')
    t_dict = {'X': abs(t[0]), 'Y': abs(t[1]), 'Z': abs(t[2])}
    axial = max(t_dict, key=t_dict.get)
    pm.delete([loc1, loc2])
    return axial


def ikfkMatch_jointMode(FK1, FK2, FK3, switchCtrl, switchAttr, switch0isfk=1, switchAttrRange=1,
                        joint_list = ['fk1', 'fk2', 'fk3'], joint_offset = [], f2_rotateAxis = '+Y'):
    loc1 = loc_create_world(joint_list[0])
    pm.parent(loc1, joint_list[0])
    pm.setAttr(loc1+'.translate', joint_offset[0][0:3])
    pm.setAttr(loc1 + '.rotate', joint_offset[0][3:6])
    pm.parent(loc1, world=True)

    loc2 = loc_create_world(joint_list[1])
    pm.parent(loc2, joint_list[1])
    pm.setAttr(loc2 + '.translate', joint_offset[1][0:3])
    pm.setAttr(loc2 + '.rotate', joint_offset[1][3:6])
    pm.parent(loc2, world=True)

    loc3 = loc_create_world(joint_list[2])
    pm.parent(loc3, joint_list[2])
    pm.setAttr(loc3 + '.translate', joint_offset[2][0:3])
    pm.setAttr(loc3 + '.rotate', joint_offset[2][3:6])
    pm.parent(loc3, world=True)

    # FK1=========================================================
    # 切换成FK
    if switch0isfk == 1:
        pm.setAttr(switchAttr, 0)
    else:
        pm.setAttr(switchAttr, switchAttrRange)
    # 求扭转轴向
    axial = twist_axial(FK1, FK2)
    # 大臂对齐
    align_obj_world(loc1, FK1)
    # loc_fk1 = loc_create_world(joint_list[0])
    # pm.parent(loc_fk1, loc1)
    # offset_FK1 = pm.getAttr(loc_fk1 + '.rotate')
    # pm.delete(loc_fk1)
    # pm.rotate(FK1, [0 - i for i in offset_FK1], r=True, os=True, fo=True)
    # 通过小臂的扭转来获取扭转值而修正大臂
    # 归零小臂
    try:
        pm.setAttr(FK2 + '.rotateX', 0)
    except:
        pass
    try:
        pm.setAttr(FK2 + '.rotateY', 0)
    except:
        pass
    try:
        pm.setAttr(FK2 + '.rotateZ', 0)
    except:
        pass
    # 打直小臂
    loc_fk2_1 = loc_create_world(joint_list[1])
    pm.parent(loc_fk2_1, loc1)
    r = pm.getAttr(loc_fk2_1 + '.rotate' + f2_rotateAxis[1])
    if 'X' in f2_rotateAxis:
        pm.rotate(FK2, [0-r, 0, 0], r=True, os=True)
    elif 'Y' in f2_rotateAxis:
        pm.rotate(FK2, [0, 0-r, 0], r=True, os=True)
    elif 'Z' in f2_rotateAxis:
        pm.rotate(FK2, [0, 0, 0-r], r=True, os=True)

    # 把以小臂为父并且对齐小臂的loc父关系给LOC2，获取axial轴向的数值
    pm.parent(loc_fk2_1, FK2)
    pm.setAttr(loc_fk2_1 + '.rotate', [0, 0, 0])
    pm.parent(loc_fk2_1, loc2)
    offset = pm.getAttr(loc_fk2_1 + '.rotate' + axial)

    # 大臂在axial轴向转动-获取的axial轴向的数值
    if abs(offset) > 0.001:
        if abs(offset) > 90:
            if offset > 0:
                offset = offset - 180
            elif offset < 0:
                offset = offset + 180
        if axial == 'X':
            pm.rotate(FK1, [0 - offset, 0, 0], r=True, os=True)
        elif axial == 'Y':
            pm.rotate(FK1, [0, 0 - offset, 0], r=True, os=True)
        elif axial == 'Z':
            pm.rotate(FK1, [0, 0, 0 - offset], r=True, os=True)
    pm.delete(loc_fk2_1)

    # FK2=========================================================
    loc_fk2 = loc_create_world(FK2)
    pm.parent(loc_fk2, loc2)
    rotate_offset = pm.getAttr(loc_fk2 + '.rotate')
    if 'X' in f2_rotateAxis:
        if round(abs(rotate_offset[1])) in range(10) and round(abs(rotate_offset[2])) in range(10):
            pm.rotate(FK2, [0 - rotate_offset[0], 0, 0], r=True, os=True)
        elif round(abs(rotate_offset[1])) in range(170, 181) or round(abs(rotate_offset[2])) in range(170, 181):
            pm.rotate(FK2, [rotate_offset[0] - 180, 0, 0], r=True, os=True)
    elif 'Y' in f2_rotateAxis:
        if round(abs(rotate_offset[0])) in range(10) and round(abs(rotate_offset[2])) in range(10):
            pm.rotate(FK2, [0, 0 - rotate_offset[1], 0], r=True, os=True)
        elif round(abs(rotate_offset[0])) in range(170, 181) or round(abs(rotate_offset[2])) in range(170, 181):
            pm.rotate(FK2, [0, rotate_offset[1] - 180, 0], r=True, os=True)
    elif 'Z' in f2_rotateAxis:
        if round(abs(rotate_offset[0])) in range(10) and round(abs(rotate_offset[1])) in range(10):
            pm.rotate(FK2, [0, 0, 0 - rotate_offset[2]], r=True, os=True)
        elif round(abs(rotate_offset[0])) in range(170, 181) or round(abs(rotate_offset[1])) in range(170, 181):
            pm.rotate(FK2, [0, 0, rotate_offset[2] - 180], r=True, os=True)

    # FK3=========================================================
    align_obj_world(loc3, FK3)
    # 收尾清除loc
    pm.delete([loc1, loc2, loc3, loc_fk2])
    pm.setKeyframe([FK1, FK2, FK3, switchCtrl], t=pm.currentTime(), s=0)

def get_variable_name(var_value, main_var):
    mvar = [key for key, val in main_var.items() if val == var_value][0]
    _logger.info('var: %s >> %s' % (mvar, var_value))  # 123 {'test_var': 123} test_var
    return [mvar, var_value]


def matchTransform(slave, master, rot=1, pos=1):
    '''
    Mimicking innate matchTransform of maya 2016.5 and up
    Args:
        slave: this object will be moved to master
        master: target position and rotation
    '''

    if rot == 0:
        skipRotAxis = ["x", "y", "z"]
    else:
        skipRotAxis = []
    if pos == 0:
        skipTransAxis = ["x", "y", "z"]
    else:
        skipTransAxis = []

    if rot == 1:
        target = pm.xform(master, q=1, ro=1, ws=1)
        pm.xform(slave, ro=target, ws=1)

    if pos == 1:
        target = pm.xform(master, q=1, t=1, ws=1)
        pm.xform(slave, t=target, ws=1)


# Align with Parent Constrain
def snap(master=None, slave=None, pos=1, rot=1):
    '''
    Snap slave to master. Check if attribute locked and skip
    '''
    lastSel = pm.selected()

    if master == None:
        master = pm.selected()[0]
    if slave == None:
        slave = pm.selected()[1:]
    slaves = pm.ls(slave)

    ptC, ptR = [], []

    # for each slave, parentconstrain for each position and rotation, skipping locked attributes
    for slave in slaves:

        slaveDup = pm.duplicate(slave, parentOnly=True)[0]
        _logger.debug('snapping slaveDup')

        # unlock all of duplicate A's arrtibutes
        basicTransforms = ['translateX', 'translateY', 'translateZ', 'translate', 'rotateX', 'rotateY', 'rotateZ',
                           'rotate']
        for attr in basicTransforms:
            # unlock attr
            pm.setAttr((slaveDup + '.' + attr), lock=False, k=1)

        ptC = pm.parentConstraint(master, slaveDup, mo=False)

        if pos == 1:
            for att in ['tx', 'ty', 'tz']:
                if pm.getAttr('%s.%s' % (slave, att), l=1) == False:
                    pm.setAttr((slave + '.' + att), pm.getAttr((slaveDup + '.' + att)))

                    _logger.info('Snap Constraining Traslation %s %s. Skiplist is ' % (master, slave))

        if rot == 1:
            for att in ['rx', 'ry', 'rz']:
                if pm.getAttr('%s.%s' % (slave, att), l=1) == False:
                    pm.setAttr((slave + '.' + att), pm.getAttr((slaveDup + '.' + att)))

                    _logger.info('Snap Constraining Rotation %s %s. Skiplist is ' % (master, slave))

        pm.delete(ptC)
        pm.delete(slaveDup)

    pm.select(lastSel)


def poleVectorPosition(startJnt, midJnt, endJnt, length=12, createLoc=0):
    import maya.api.OpenMaya as om

    start = pm.xform(startJnt, q=1, ws=1, t=1)
    mid = pm.xform(midJnt, q=1, ws=1, t=1)
    end = pm.xform(endJnt, q=1, ws=1, t=1)
    startV = om.MVector(start[0], start[1], start[2])
    midV = om.MVector(mid[0], mid[1], mid[2])
    endV = om.MVector(end[0], end[1], end[2])

    startEnd = endV - startV
    startMid = midV - startV

    # projection vector is vecA projected onto vecB
    # it is calculated by dot product if one vector normalized

    # proj= vecA * vecB.normalized (dot product result is scalar)
    proj = startMid * startEnd.normal()

    # multiply proj scalar with normalized startEndVector to project it onto vector
    startEndN = startEnd.normal()
    projV = startEndN * proj

    arrowV = startMid - projV
    arrowVN = arrowV.normal()

    # scale up to length and offset to midV
    finalV = arrowVN * length + midV

    if createLoc:
        loc = pm.spaceLocator(n='polePos')
        pm.xform(loc, ws=1, t=(finalV.x, finalV.y, finalV.z))
        return loc

    return finalV


def unlockAttributes(objects, attributes=['translateX', 'translateY', 'translateZ', 'rotateX', '  rotateY', 'rotateZ','visibility']):
    # unlock all of duplicate A's arrtibutes
    for obj in objects:
        for attr in attributes:
            # unlock attr
            pm.setAttr((obj + '.' + attr), lock=False, k=True)
            pm.setAttr((obj + '.' + attr), lock=False, k=True)
            pm.setAttr((obj + '.' + attr), lock=False, k=True)
            if attr == 'visibility':
                pm.setAttr((obj + '.' + attr), 1)


def orientJoints(joints, aimAxis, upAxis, upDir, doAuto):
    """
    *
    *  $joints is array of joints to orient
    *  $aimAxis = is xyz array of what axis of joint does aim
    *  $upAxis = is xyz array of what axis of joint does up
    *  $upDir = what vector to use for up direction?
    *  $doAuto = If possible will try to guess the up axis otherwise
    *      it will use prev joint up axis or else world upDir.
    *
    """

    nJnt = len(joints)
    i = 0
    prevUp = pm.dt.Vector([0, 0, 0])
    # Now orient each joint
    for i in range(0, nJnt):
        childs = pm.listRelatives(joints[i], type=["transform", "joint"], children=1)
        # First we need to unparent everything and then store that,
        if len(childs) > 0:
            childs = pm.parent(childs, w=1)
        # unparent and get NEW names in case they changed...
        # Find parent for later in case we need it.

        parents = pm.listRelatives(joints[i], parent=1)
        parent = parents[0]
        # Now if we have a child joint...aim to that.
        aimTgt = ""
        child = ""
        for child in childs:
            if pm.nodeType(child) == "joint":
                aimTgt = str(child)
                break

        if aimTgt != "":
            upVec = [0, 0, 0]
            # First off...if $doAuto is on, we need to guess the cross axis dir.
            #
            if doAuto:
                posJ = pm.xform(joints[i], q=1, rp=1, ws=1)
                # Now since the first joint we want to match the second orientation
                # we kind of hack the things passed in if it is the first joint
                # ie: If the joint doesn't have a parent...OR if the parent it has
                # has the "same" position as itself...then we use the "next" joints
                # as the up cross calculations
                #
                posP = posJ
                if parent != "":
                    posP = pm.xform(parent, q=1, rp=1, ws=1)

                tol = 0.0001
                # How close to we consider "same"?
                if parent == "" or (abs(posJ[0] - posP[0]) <= tol and abs(posJ[1] - posP[1]) <= tol and abs(
                        posJ[2] - posP[2]) <= tol):
                    aimChilds = pm.listRelatives(aimTgt, children=1)
                    aimChild = ""
                    child = ""
                    for child in aimChilds:
                        if pm.nodeType(child) == "joint":
                            aimChild = str(child)
                            break

                    upVec = pm.mel.cJO_getCrossDir(joints[i], aimTgt, aimChild)


                else:
                    upVec = pm.mel.cJO_getCrossDir(parent, joints[i], aimTgt)

            if not doAuto or (upVec[0] == 0.0 and upVec[1] == 0.0 and upVec[2] == 0.0):
                upVec = upDir
            # or else use user set up Dir. if needed

            aCons = pm.aimConstraint(aimTgt, joints[i],
                                     aim=(aimAxis[0], aimAxis[1], aimAxis[2]),
                                     worldUpType="vector",
                                     weight=1.0,
                                     upVector=(upAxis[0], upAxis[1], upAxis[2]),
                                     worldUpVector=(upVec[0], upVec[1], upVec[2]))
            pm.delete(aCons)
            # Now compare the up we used to the prev one.
            curUp = pm.dt.Vector([upVec[0], upVec[1], upVec[2]])
            curUp = pm.dt.Vector(pm.mel.unit(curUp))
            dot = float(curUp * prevUp)
            # dot product for angle betwen...
            prevUp = pm.dt.Vector([upVec[0], upVec[1], upVec[2]])
            # store for later
            if i > 0 and dot <= 0.0:
                pm.xform(joints[i], r=1, os=1, ra=((aimAxis[0] * 180.0), (aimAxis[1] * 180.0), (aimAxis[2] * 180.0)))
                # Adjust the rotation axis 180 if it looks like we've flopped the wrong way!
                prevUp *= pm.dt.Vector(-1.0)

            pm.joint(joints[i], zso=1, e=1)
            # And now finish clearing out joint axis...
            pm.makeIdentity(joints[i], apply=True)


        elif parent != "":
            oCons = pm.orientConstraint(parent, joints[i],
                                        weight=1.0)
            # Otherwise if there is no target, just dup orienation of parent...
            pm.delete(oCons)
            # And now finish clearing out joint axis...
            pm.joint(joints[i], zso=1, e=1)
            pm.makeIdentity(joints[i], apply=True)

        if len(childs) > 0:
            pm.parent(childs, joints[i])
        # Now that we're done... reparent

if __name__ == "__main__":
    FkIk_UI()