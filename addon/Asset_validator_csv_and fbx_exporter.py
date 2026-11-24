bl_info = {
       "name" : "Validate Objects",
       "author" : "Tech Artist",
       "version" : (1,0,0),
       "blender" : (4,5,0),
       "category" : "Object"
       }
       
import bpy
import os
import csv

def check_name(obj):
    return obj.name.startswith("SM_")

def check_material(obj):
    materials = obj.data.materials
    if len(materials) == 0:
        return False
    return all(mat is not None for mat in materials)

def check_uv(obj):
    return len(obj.data.uv_layers) > 0

def calculate_triangles(obj):
    triangles = 0
    for poly in obj.data.polygons:
        triangles += poly.loop_total - 2
    return triangles 

def validate_assets(obj):
    issues = []
    
    if not check_name(obj):
        issues.append("Incorrect name convention")
        
    if not check_material(obj):
        issues.append("Material not assigned")
        
    if not check_uv(obj):
        issues.append("UV map not found")
        
    if len(issues) > 0:
        status = "Invalid"
    else:
        status = "Valid"
        
    return issues,status

def collect_asset(scene):
    report_data = []
    warning = []
    valid = 0
    invalid = 0
    total = 0
    
    for obj in scene.objects:
        if obj.type == "MESH":
            total += 1
            
            issues,status = validate_assets(obj)
            if status == "Valid":
                valid += 1
            else :
                invalid += 1
                
            obj_name = obj.name
            vertices = len(obj.data.vertices)
            edges = len(obj.data.edges)
            polygons = len(obj.data.polygons)
            
            triangles = calculate_triangles(obj)
            
            if check_material(obj):
                material = "Assigned"
            else:
                material = "Missing"
            
            if check_uv(obj):
                uv = "Assigned"
            else:
                uv = "Missing"
                
            if len(obj.data.polygons) > 1000:
                warning.append("Polygon count too high")
                
            asset_data = {
                   "Object Name" : obj_name,
                   "Vertices" : vertices,
                   "Edges" : edges,
                   "Faces" : polygons,
                   "Triangles" : triangles,
                   "Material" : material,
                   "UV Map" : uv,
                   "Status" : status,
                   "Issues" : ";".join(issues),
                   "Warnings" : ";".join(warning)
                }
            report_data.append(asset_data)
    return report_data,valid,invalid,total

class OBJECT_OT_validate_assets(bpy.types.Operator):
    bl_idname = "object.validate_objects"
    bl_label = "Scan Assets"
    bl_options = {'REGISTER'}
    
    def execute(self,context):
        scene = context.scene
        
        report_data,valid,invalid,total = collect_asset(scene)
        
        scene.asset_total = total
        scene.asset_valid = valid
        scene.asset_invalid = invalid
        scene.scan_completed = True
        
        print("=== VALIDATION REPORT ===")
        print("Total objects:",total)
        print("Valid Objects:", valid)
        print("Invalid Objects:",invalid)
        
        if total == 0:
            self.report({'WARNING'}, "No mesh objects to scan")
            return {'CANCELLED'}
        self.report({'INFO'},f"Scanning completed: {valid} valid, {invalid} invalid objects.")
        
        return {'FINISHED'}
    
class OBJECT_OT_csv_file_generator(bpy.types.Operator):
    bl_idname = "object.csv_report"
    bl_label = "Generate CSV Report"
    bl_options = {'REGISTER'}
    
    def execute(self,context):
        scene = context.scene
        report_data,valid,invalid,total = collect_asset(scene)
        
        if total == 0:
            self.report({'WARNING'},"No objects to export")
            return {'CANCELLED'}
        
        scene.asset_total = total
        scene.asset_valid = valid
        scene.asset_invalid = invalid
        scene.scan_completed = True
        
        folder = os.path.expanduser("~/Desktop/AssetPipeline/Report")
        os.makedirs(folder,exist_ok = True)
        file_path = os.path.join(folder , "AssetValidator2.csv")
        
        headers = ["Object Name","Vertices","Edges","Faces","Triangles","Material","UV Map","Status","Issues","Warnings"]
        
        try:
            with open(file_path, mode = 'w',newline = "",encoding = "utf-8") as file:
                writer = csv.DictWriter(
                         file,
                         fieldnames = headers
                         )
                writer.writeheader()
                writer.writerows(report_data)
        
        except OSError as error:
            self.report ({'ERROR'},f"Could not save report {error}")
            return {'CANCELLED'}
        
        print("\nCSV report saved at:", file_path)
        self.report ({'INFO'},"CSV report exported successfully")
        return {'FINISHED'}

class OBJECT_OT_export_fbx_file(bpy.types.Operator):
    bl_idname = "object.export_fbx_file"
    bl_label = "FBX File Exporter"
    bl_options = {'REGISTER'}
    
    def execute(self,context):
        export_folder = os.path.expanduser("~/Desktop/AssetPipeline/Exports")
        os.makedirs(export_folder, exist_ok = True)
        
        exported = 0
        skipped = 0
        failed = 0
        
        original_selection = list(context.selected_objects)
        original_active = context.view_layer.objects.active
        
        try:
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode = 'OBJECT')
                
            scene = context.scene
            for obj in scene.objects:
                if obj.type != 'MESH':
                    continue 
                issues,status = validate_assets(obj)
                if status != "Valid":
                    skipped += 1
                    print("Skipped:",obj.name)
                    continue
                    
                try:
                    bpy.ops.object.select_all(action = "DESELECT")
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    
                    safe_name = bpy.path.clean_name(obj.name)
                    file_path = os.path.join(export_folder,safe_name + ".fbx")
                    
                    result = bpy.ops.export_scene.fbx(
                              filepath = file_path,
                              use_selection = True,
                              apply_scale_options = "FBX_SCALE_ALL"
                              )
                    if 'FINISHED' in result:
                        exported += 1
                        print("Exported:",obj.name)
                    else:
                        failed += 1
                        print("Export Failed:", obj.name)
                    
                except Exception as error:
                    failed += 1
                    print("Export error:",obj.name,error)
                    
        finally:
            
            for obj in original_selection :
                if obj.name in context.view_layer.objects:
                    obj.select_set(True)
                    
            if (original_active is not None and original_active.name in context.view_layer.objects):
                context.view_layer.objects.active = original_active
                
        print("\n==== BATCH EXPORT RESULTS ===")
        print("\nExported assets:",exported)
        print("Skipped:",skipped)
        print("Failed:",failed)
        
        self.report({'INFO'},f"Exported objects: {exported},Skipped: {skipped},Failed : {failed}")
        return {'FINISHED'}        

    
class VIEW3D_PT_asset_validator(bpy.types.Panel):
    bl_idname = "VIEW_3D_PT_asset_validator"
    bl_label = "Asset Pipeline Tool 1"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "My Tools"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.label(text = "Asset validator")
        layout.operator (
                "object.validate_objects",
                text = "Scan Assets",
                icon = "VIEWZOOM"
                )
        layout.operator(
                "object.csv_report",
                text = "Generate CSV Report",
                icon = "EXPORT"
                )
        layout.operator(
                "object.export_fbx_file",
                text = "Export the FBX Files",
                icon = "EXPORT"
                )
        if scene.scan_completed:
            layout.separator()
            layout.label (text = "Validation Results",icon = "INFO")
            layout.label (text = f"Total Assets : {scene.asset_total}")
            layout.label (text = f"Valid Assets : {scene.asset_valid}",icon = "CHECKMARK")
            layout.label (text = f"Invalid Assets : {scene.asset_invalid}",icon = "ERROR")
            
            layout.separator()
            
            layout.label (text = "Assets needing Attention!", icon = 'ERROR')
            needs_attention = False
            
            for obj in scene.objects:
                if obj.type == "MESH":
                    issues,status = validate_assets(obj)
                    
                    poly_count = len(obj.data.polygons) > 1000
                    
                    if issues or poly_count:
                        
                        needs_attention = True
                        box = layout.box()
                        box.label(text = obj.name, icon = 'OBJECT_DATA')
                        for issue in issues:
                            box.label(text = issue,icon = 'ERROR')
                            if poly_count:
                                box.label (text = "High Polygon Count",icon = 'ERROR')
                        
            if not needs_attention:
                layout.label(text = "All assets passed Validation!",icon = 'CHECKMARK')
                            
                
            
            

classes = (
      OBJECT_OT_validate_assets,
      OBJECT_OT_csv_file_generator,
      OBJECT_OT_export_fbx_file,
      VIEW3D_PT_asset_validator
    )
    
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.asset_total = bpy.props.IntProperty(
           name = "Total Assets",
           default = 0
        )
    
    bpy.types.Scene.asset_valid = bpy.props.IntProperty(
           name = "Valid",
           default = 0
        )
    bpy.types.Scene.asset_invalid = bpy.props.IntProperty(
           name = "Invalid",
           default = 0
        )
    bpy.types.Scene.scan_completed = bpy.props.BoolProperty(
           name = "Scan Completed",
           default = False
        )
        
def unregister():
    properties = (
           "asset_total",
           "asset_valid",
           "asset_invalid",
           "scan_completd"
        )
    
    for props in properties:
        if hasattr(bpy.types.Scene, props):
            delattr(bpy.types.Scene, props)
           
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        
        
if __name__ == "__main__":
    try :
        unregister()
    except Exception:
        pass
    
    register()
    
        

           
        
      
        
                  
                
        
