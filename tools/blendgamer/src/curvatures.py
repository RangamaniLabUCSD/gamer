# ***************************************************************************
# This file is part of the GAMer software.
# Copyright (C) 2016-2018
# by Christopher Lee, Tom Bartol, John Moody, Rommie Amaro, J. Andrew McCammon,
#    and Michael Holst

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
# ***************************************************************************

import bpy
import bmesh
from bpy.props import (
        BoolProperty, CollectionProperty, EnumProperty,
        FloatProperty, FloatVectorProperty, IntProperty, IntVectorProperty,
        PointerProperty, StringProperty, BoolVectorProperty)
from blendgamer.colormap_enums import colormap_enums

import importlib.util
mpl_spec = importlib.util.find_spec("matplotlib")
mpl_found = mpl_spec is not None

if mpl_found:
    from blendgamer.colormap import dataToVertexColor

from blendgamer.util import *

curvatureTypeEnums = [
    ('K1', 'k1', 'First principle curvature'),
    ('K2', 'k2', 'Second principle curvature'),
    ('KG', 'kg', 'Gaussian curvature'),
    ('KH', 'kh', 'Mean curvature'),
]

curvatureCalcEnums = [
    ('MDSB', 'MDSB', 'Meyer, Desbrun, Schroder, Barr Algorithm'),
    ('JETS', 'Jet Fitting', 'Cazal and Pouget Jet Fitting'),
]
curvatureCalcDict = {
  'MDSB': 'curvatureViaMDSB',
  'JETS' : 'curvatureViaJets',
}

class GAMER_OT_remove_curvature(bpy.types.Operator):
    bl_idname       = "gamer.remove_curvature"
    bl_label        = "Remove Curvature"
    bl_description  = "Remove selected curvature from object"
    bl_options      = {'REGISTER'}

    def execute(self, context):
        context.object.gamer.curvatures.remove_curvature(context, self.report)
        return {'FINISHED'}

class GAMER_OT_remove_all_curvatures(bpy.types.Operator):
    bl_idname       = "gamer.remove_all_curvatures"
    bl_label        = "Remove All Curvatures"
    bl_description  = "Remove all curvatures from object"
    bl_options      = {'REGISTER'}

    def execute(self, context):
        context.object.gamer.curvatures.remove_all_curvatures(context, self.report)
        return {'FINISHED'}

class GAMER_OT_curvature_to_colormap(bpy.types.Operator):
    bl_idname       = "gamer.curvature_to_colormap"
    bl_label        = "Apply vertex colorings from curvature"
    bl_description  = "Map curvature values into vertex colors"
    bl_options      = {'REGISTER'}

    def execute(self, context):
        context.object.gamer.curvatures.curvature_to_colormap(context, self.report)
        return {'FINISHED'}

class GAMER_OT_compute_curvatures(bpy.types.Operator):
    bl_idname       = "gamer.compute_curvatures"
    bl_label        = "Compute Curvatures"
    bl_description  = "Compute curvatures"
    bl_options      = {'REGISTER'}

    def execute(self, context):
        obj = getActiveMeshObject(self.report)
        if obj.gamer.curvatures.compute_curvatures(context, self.report):
            self.report({'INFO'}, "GAMer: Compute Curvatures complete")
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

class GAMerCurvatureItem(bpy.types.PropertyGroup):
    curvatureType = EnumProperty(
        name = "Curvature Type",
        description = "Which curvature?",
        items = curvatureTypeEnums
        )
    algorithm = EnumProperty(
        name = "Curvature algorithm used",
        description = "Which algorithm was used?",
        items = curvatureCalcEnums
    )

    ## Addition metadata for saving plot states...
    minCurve = FloatProperty(
        name="Minimum curvature", default=0,
        description="Lower bound percentile truncation"
        )
    maxCurve = FloatProperty(
        name="Maximum curvature", default=1000,
        description="Upper bound percentile truncation"
        )
    curveIter = IntProperty(
        name="Smooth Curvature Iterations", min=0, default = 5,
        description="How many iterations of curvature smoothing?"
        )
    curvePercentile = BoolProperty(
        name="Use Percentiles", default = True,
        description="Treat min and max as percentiles?"
        )
    mixpoint = FloatProperty(
        name = "Color mixing point", default = 0.5, min=0, max=1,
        description="Value for color mixing"
        )
    colormap = EnumProperty(
            name = "Colormap colors",
            description="Colormap used",
            items = colormap_enums,
        )


class GAMerCurvaturesList(bpy.types.PropertyGroup):
    algorithm = EnumProperty(
        name = "Curvature Algorithm",
        description = "Which algorithm was used?",
        items = curvatureCalcEnums
    )
    curvature_list = CollectionProperty(
                            type=GAMerCurvatureItem,
                            name="List of computed curvatures"
                        )
    active_index = IntProperty(
                            name="Active Index",
                            default=0
                        )

    showplots = BoolProperty(
        name="Show plot", default=False,
        description="Display the plots"
        )

    saveplots = BoolProperty(
        name="Save plots", default=False,
        description="Save the generated plots"
        )

    def compute_curvatures(self, context, report):
        obj = getActiveMeshObject(report)
        gmesh = blenderToGamer(report)
        if gmesh:
            kh, kg, k1, k2 = getattr(gmesh, curvatureCalcDict[self.algorithm])(0)

            with ObjectMode():
                ml = getCurvatureLayer(obj, self.algorithm, 'K1')
                for i in range(0, len(k1)):
                    ml[i].value = k1[i]
                self.add_curvature(context, 'K1')

                ml = getCurvatureLayer(obj, self.algorithm, 'K2')
                for i in range(0, len(k1)):
                    ml[i].value = k2[i]
                self.add_curvature(context, 'K2')

                ml = getCurvatureLayer(obj, self.algorithm, 'KG')
                for i in range(0, len(k1)):
                    ml[i].value = kg[i]
                self.add_curvature(context, 'KG')

                ml = getCurvatureLayer(obj, self.algorithm, 'KH')
                for i in range(0, len(k1)):
                    ml[i].value = kh[i]
                self.add_curvature(context, 'KH')

            del kh
            del kg
            del k1
            del k2
            return True
        return False

    def add_curvature(self, context, curvatureType):
        if len(self.curvature_list) > 0:
            for c in self.curvature_list:
                if c.algorithm == self.algorithm:
                    if c.curvatureType == curvatureType:
                        return False
        new_curve = self.curvature_list.add()
        new_curve.curvatureType = curvatureType
        new_curve.algorithm = self.algorithm


    def remove_curvature(self, context, report):
        crv = self.get_active_index()
        if crv:
            obj = getActiveMeshObject(report)
            bm = bmesh_from_object(obj)

            name = "%s%s"%(crv.algorithm, crv.curvatureType)
            layer = bm.verts.layers.float[name]
            bm.verts.layers.float.remove(layer)

            bmesh_to_object(obj,bm)

            self.curvature_list.remove(self.active_index)
            self.active_index -= 1
            if (self.active_index < 0):
                self.active_index = 0

    def remove_all_curvatures(self, context, report):
        obj = getActiveMeshObject(report)
        bm = bmesh_from_object(obj)

        for i in range(len(self.curvature_list)):
            crv = self.curvature_list[0]

            name = "%s%s"%(crv.algorithm, crv.curvatureType)
            layer = bm.verts.layers.float[name]
            bm.verts.layers.float.remove(layer)
            self.curvature_list.remove(0)

        bmesh_to_object(obj,bm)
        self.active_index = 0

    def curvature_to_colormap(self, context, report):
        obj = getActiveMeshObject(report)
        with ObjectMode():
            bm = bmesh_from_object(obj)

            crv = self.get_active_index()
            layer = getCurvatureLayer(obj, self.algorithm, 'K1')

            data = np.zeros(len(obj.data.vertices), dtype=np.float)
            # Copy curvatures over
            layer.foreach_get('value', data)


            if crv.curveIter > 0:
                for i in range(0, crv.curveIter):
                    # adjacency = np.zeroes(len(obj.data.vertices), dtype=np.int)
                    tmp = np.zeros(len(obj.data.vertices), dtype=np.int)
                    for v in bm.verts:
                        count = 1
                        tmp[v.index] = data[v.index]

                        for e in v.link_edges:
                            v_other = e.other_vert(v)

                            tmp[v.index] += data[v_other.index]
                            count += 1
                        tmp[v.index] /= count
                    data = np.array(tmp, copy=True)
                    print(data)

            dataToVertexColor(data, minV=crv.minCurve, maxV=crv.maxCurve,
                        percentTruncate=crv.curvePercentile,
                        vlayer="FOO",
                        axislabel="FOO [$\mu m^{-1}$]",
                        file_prefix="%s_%s_m%d_M%d_I%d_Curvature"%(bpy.path.basename(bpy.context.blend_data.filepath).split('.')[0], context.object.name, crv.minCurve, crv.maxCurve, crv.curveIter),
                        showplot=self.showplots,saveplot=self.saveplots, mixpoint=crv.mixpoint, colormap=crv.colormap)
            bm.free()


    def get_active_index(self):
        idx = None
        if len(self.curvature_list) > 0:
            idx = self.curvature_list[self.active_index]
        return idx

    def make_plot(self):
        pass

    def toVertexColors(self):
        pass

classes = [GAMER_OT_compute_curvatures,
           GAMER_OT_remove_curvature,
           GAMER_OT_remove_all_curvatures,
           GAMER_OT_curvature_to_colormap,
           GAMerCurvatureItem,
           GAMerCurvaturesList]

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(make_annotations(cls))

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(make_annotations(cls))
