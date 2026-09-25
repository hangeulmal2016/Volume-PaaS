import io
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from scipy.spatial import KDTree, ConvexHull
from shapely.geometry import Polygon, Point
from app.utils import export_to_excel, export_to_dxf

app = FastAPI(title="PaaS Spatial Grid Volume Engine")

# Cho phép mọi thiết bị smartphone truy cập API không bị chặn CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def parse_txt_file(contents: bytes, col_x: int, col_y: int, col_z: int):
    lines = contents.decode("utf-8").strip().split("\n")
    points = []
    for line in lines:
        if not line.strip() or line.strip().startswith(("#", "//")):
            continue
        tokens = line.replace(";", " ").replace(",", " ").split()
        try:
            if len(tokens) > max(col_x, col_y, col_z):
                points.append([float(tokens[col_x]), float(tokens[col_y]), float(tokens[col_z])])
        except ValueError:
            continue
    if len(points) == 0:
        raise HTTPException(status_code=400, detail="Lỗi định dạng cấu trúc file TXT.")
    return np.array(points)

def idw_interpolator(tree, z_data, target_xy, p=2, k=12):
    distances, indices = tree.query(target_xy, k=k)
    if np.any(distances == 0):
        return z_data[indices[np.where(distances == 0)[0][0]]]
    weights = 1.0 / (distances ** p)
    return np.sum(weights * z_data[indices]) / np.sum(weights)

@app.post("/api/preview-txt")
async def preview_txt(file: UploadFile = File(...)):
    contents = await file.read()
    lines = contents.decode("utf-8").split("\n")
    preview_lines = [line.strip().replace(",", " ").replace(";", " ").split() for line in lines if line.strip()][:5]
    return {"preview": preview_lines}

@app.post("/api/calculate")
async def calculate_volume(
    file_bm1: UploadFile = File(None), file_bm2: UploadFile = File(None), file_boundary: UploadFile = File(None),
    bm1_x: int = Form(0), bm1_y: int = Form(1), bm1_z: int = Form(2),
    bm2_x: int = Form(0), bm2_y: int = Form(1), bm2_z: int = Form(2),
    bm1_fixed_z: float = Form(None), bm2_fixed_z: float = Form(None),
    grid_size: float = Form(5.0)
):
    pts_bm1 = parse_txt_file(await file_bm1.read(), bm1_x, bm1_y, bm1_z) if (file_bm1 and bm1_fixed_z is None) else None
    pts_bm2 = parse_txt_file(await file_bm2.read(), bm2_x, bm2_y, bm2_z) if (file_bm2 and bm2_fixed_z is None) else None

    # Module Tự động nhận diện ranh giới chu vi
    if file_boundary:
        bound_pts = parse_txt_file(await file_boundary.read(), 0, 1, 0)[:, :2]
        boundary_poly = Polygon(bound_pts)
    else:
        ref_pts = pts_bm1 if pts_bm1 is not None else pts_bm2
        if pts_bm1 is not None and pts_bm2 is not None:
            poly1 = Polygon(pts_bm1[ConvexHull(pts_bm1[:, :2]).vertices, :2])
            poly2 = Polygon(pts_bm2[ConvexHull(pts_bm2[:, :2]).vertices, :2])
            boundary_poly = poly1.intersection(poly2)
        else:
            boundary_poly = Polygon(ref_pts[ConvexHull(ref_pts[:, :2]).vertices, :2])

    if boundary_poly.is_empty:
        raise HTTPException(status_code=400, detail="Vùng dữ liệu hai bề mặt không chồng lấn.")

    min_x, min_y, max_x, max_y = boundary_poly.bounds
    x_coords = np.arange(min_x + grid_size/2, max_x, grid_size)
    y_coords = np.arange(min_y + grid_size/2, max_y, grid_size)
    
    tree_bm1 = KDTree(pts_bm1[:, :2]) if pts_bm1 is not None else None
    tree_bm2 = KDTree(pts_bm2[:, :2]) if pts_bm2 is not None else None

    grid_results = []
    total_cut, total_fill = 0.0, 0.0
    cell_area = grid_size * grid_size

    for r_idx, y in enumerate(y_coords):
        for c_idx, x in enumerate(x_coords):
            if not boundary_poly.contains(Point(x, y)):
                continue
            z1 = bm1_fixed_z if bm1_fixed_z is not None else idw_interpolator(tree_bm1, pts_bm1[:, 2], [x, y])
            z2 = bm2_fixed_z if bm2_fixed_z is not None else idw_interpolator(tree_bm2, pts_bm2[:, 2], [x, y])
            dh = z2 - z1
            v_cell = cell_area * dh
            cut_v = abs(v_cell) if dh < 0 else 0.0
            fill_v = v_cell if dh > 0 else 0.0
            total_cut += cut_v
            total_fill += fill_v
            
            grid_results.append({"row": int(r_idx), "col": int(c_idx), "x": float(x), "y": float(y), "z1": float(z1), "z2": float(z2), "dh": float(dh), "cut": float(cut_v), "fill": float(fill_v)})

    return {
        "summary": {"cut": round(total_cut, 2), "fill": round(total_fill, 2), "net": round(total_fill - total_cut, 2), "cells": len(grid_results)},
        "grid_data": grid_results, "grid_size": grid_size
    }

@app.post("/api/export/excel")
async def export_excel(data: list):
    output = export_to_excel(data)
    return StreamingResponse(io.BytesIO(output), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=bao_cao_khoi_luong.xlsx"})

@app.post("/api/export/dxf")
async def export_dxf(payload: dict):
    output = export_to_dxf(payload["grid_data"], payload["grid_size"])
    return StreamingResponse(io.BytesIO(output), media_type="application/dxf", headers={"Content-Disposition": "attachment; filename=ban_ve_luoi.dxf"})
