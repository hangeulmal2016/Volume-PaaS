import io
import openpyxl
import ezdxf

def export_to_excel(grid_data: list):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Khoi Luong Luoi"
    ws.append(["Hang", "Cot", "Toa do X", "Toa do Y", "Cao do BM1", "Cao do BM2", "Chenh Cao", "V Dao (m3)", "V Dap (m3)"])
    for r in grid_data:
        ws.append([r['row'], r['col'], round(r['x'],2), round(r['y'],2), round(r['z1'],2), round(r['z2'],2), round(r['dh'],2), round(r['cut'],2), round(r['fill'],2)])
    stream = io.BytesIO()
    wb.save(stream)
    return stream.getvalue()

def export_to_dxf(grid_data: list, grid_size: float):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    doc.layers.new(name='Luoi_O_Vuong', color=7)
    doc.layers.new(name='Text_Ghi_Chu', color=2)
    half = grid_size / 2.0
    for item in grid_data:
        x, y = item['x'], item['y']
        corners = [(x-half, y-half), (x+half, y-half), (x+half, y+half), (x-half, y+half), (x-half, y-half)]
        msp.add_lwpolyline(corners, dxfattribs={'layer': 'Luoi_O_Vuong'})
        msp.add_text(f"h:{round(item['dh'],2)}", dxfattribs={'layer': 'Text_Ghi_Chu', 'height': grid_size*0.15}).set_placement((x, y))
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode('utf-8')
