from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel
from typing import Optional

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Base, Feature

import json
import csv
import io
import zipfile
import tempfile
from pathlib import Path

import shapefile


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


app = FastAPI(
    title="SpatioraMap",
    version="0.4.0",
    description="Mini GIS Digitizing Application"
)


class FeatureData(BaseModel):
    geometry_type: str
    geometry: dict
    name: str
    asset_type: str
    description: Optional[str] = ""
    status: str = "Active"


@app.get("/")
def read_root():
    return FileResponse(
        FRONTEND_DIR / "index.html"
    )


@app.post("/features")
def create_feature(data: FeatureData):

    allowed_types = [
        "Point",
        "LineString",
        "Polygon"
    ]

    if data.geometry_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid geometry type."
        )

    db: Session = SessionLocal()

    try:

        feature = Feature(
            geometry_type=data.geometry_type,
            geometry=json.dumps(data.geometry),
            name=data.name,
            asset_type=data.asset_type,
            description=data.description,
            status=data.status
        )

        db.add(feature)
        db.commit()
        db.refresh(feature)

        return {
            "id": feature.id,
            "message": "Feature saved successfully."
        }

    finally:
        db.close()


@app.get("/features")
def get_features():

    db: Session = SessionLocal()

    try:

        features = (
            db.query(Feature)
            .order_by(Feature.id.desc())
            .all()
        )

        result = []

        for feature in features:

            result.append({
                "id": feature.id,
                "geometry_type": feature.geometry_type,
                "geometry": json.loads(feature.geometry),
                "name": feature.name,
                "asset_type": feature.asset_type,
                "description": feature.description or "",
                "status": feature.status or "Active",
                "created_at": (
                    feature.created_at.isoformat()
                    if feature.created_at
                    else None
                )
            })

        return result

    finally:
        db.close()


@app.get("/features/{feature_id}")
def get_feature(feature_id: int):

    db: Session = SessionLocal()

    try:

        feature = (
            db.query(Feature)
            .filter(Feature.id == feature_id)
            .first()
        )

        if not feature:
            raise HTTPException(
                status_code=404,
                detail="Feature not found."
            )

        return {
            "id": feature.id,
            "geometry_type": feature.geometry_type,
            "geometry": json.loads(feature.geometry),
            "name": feature.name,
            "asset_type": feature.asset_type,
            "description": feature.description or "",
            "status": feature.status or "Active",
            "created_at": (
                feature.created_at.isoformat()
                if feature.created_at
                else None
            )
        }

    finally:
        db.close()


@app.put("/features/{feature_id}")
def update_feature(
    feature_id: int,
    data: FeatureData
):

    allowed_types = [
        "Point",
        "LineString",
        "Polygon"
    ]

    if data.geometry_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid geometry type."
        )

    db: Session = SessionLocal()

    try:

        feature = (
            db.query(Feature)
            .filter(Feature.id == feature_id)
            .first()
        )

        if not feature:
            raise HTTPException(
                status_code=404,
                detail="Feature not found."
            )

        feature.geometry_type = data.geometry_type
        feature.geometry = json.dumps(data.geometry)
        feature.name = data.name
        feature.asset_type = data.asset_type
        feature.description = data.description
        feature.status = data.status

        db.commit()
        db.refresh(feature)

        return {
            "id": feature.id,
            "message": "Feature updated successfully."
        }

    finally:
        db.close()


@app.delete("/features/{feature_id}")
def delete_feature(feature_id: int):

    db: Session = SessionLocal()

    try:

        feature = (
            db.query(Feature)
            .filter(Feature.id == feature_id)
            .first()
        )

        if not feature:
            raise HTTPException(
                status_code=404,
                detail="Feature not found."
            )

        db.delete(feature)
        db.commit()

        return {
            "message": "Feature deleted successfully."
        }

    finally:
        db.close()


@app.get("/statistics")
def get_statistics():

    db: Session = SessionLocal()

    try:

        features = (
            db.query(Feature)
            .all()
        )

        total = len(features)

        points = sum(
            1 for f in features
            if f.geometry_type == "Point"
        )

        lines = sum(
            1 for f in features
            if f.geometry_type == "LineString"
        )

        polygons = sum(
            1 for f in features
            if f.geometry_type == "Polygon"
        )

        active = sum(
            1 for f in features
            if (f.status or "Active") == "Active"
        )

        inactive = sum(
            1 for f in features
            if (f.status or "Active") == "Inactive"
        )

        return {
            "total": total,
            "points": points,
            "lines": lines,
            "polygons": polygons,
            "active": active,
            "inactive": inactive
        }

    finally:
        db.close()


def write_shapefile(
    output_directory,
    geometry_type,
    filename,
    shape_type
):

    db: Session = SessionLocal()

    try:

        features = (
            db.query(Feature)
            .filter(
                Feature.geometry_type == geometry_type
            )
            .all()
        )

        if not features:
            return False

        shp_path = (
            Path(output_directory) / filename
        )

        writer = shapefile.Writer(
            str(shp_path),
            shapeType=shape_type
        )

        writer.field(
            "ID",
            "N",
            size=10
        )

        writer.field(
            "NAME",
            "C",
            size=100
        )

        writer.field(
            "TYPE",
            "C",
            size=80
        )

        writer.field(
            "DESC",
            "C",
            size=254
        )

        writer.field(
            "STATUS",
            "C",
            size=20
        )

        for feature in features:

            geometry = json.loads(
                feature.geometry
            )

            coordinates = geometry["coordinates"]

            if geometry_type == "Point":

                x = coordinates[0]
                y = coordinates[1]

                writer.point(
                    x,
                    y
                )

            elif geometry_type == "LineString":

                writer.line(
                    [coordinates]
                )

            elif geometry_type == "Polygon":

                writer.poly(
                    coordinates
                )

            writer.record(
                feature.id,
                feature.name,
                feature.asset_type,
                feature.description or "",
                feature.status or "Active"
            )

        writer.close()

        prj_path = (
            Path(output_directory) /
            f"{filename}.prj"
        )

        prj_content = (
            'GEOGCS["GCS_WGS_1984",'
            'DATUM["D_WGS_1984",'
            'SPHEROID["WGS_1984",'
            '6378137,298.257223563]],'
            'PRIMEM["Greenwich",0],'
            'UNIT["Degree",'
            '0.0174532925199433]]'
        )

        prj_path.write_text(
            prj_content,
            encoding="utf-8"
        )

        return True

    finally:
        db.close()


@app.get("/download")
def download_data():

    temporary_directory = tempfile.mkdtemp()

    output_directory = Path(
        temporary_directory
    )

    point_created = write_shapefile(
        output_directory,
        "Point",
        "points",
        shapefile.POINT
    )

    line_created = write_shapefile(
        output_directory,
        "LineString",
        "lines",
        shapefile.POLYLINE
    )

    polygon_created = write_shapefile(
        output_directory,
        "Polygon",
        "polygons",
        shapefile.POLYGON
    )

    db: Session = SessionLocal()

    try:

        features = (
            db.query(Feature)
            .order_by(Feature.id)
            .all()
        )

        csv_path = (
            output_directory /
            "all_attributes.csv"
        )

        with open(
            csv_path,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as csv_file:

            writer = csv.writer(csv_file)

            writer.writerow([
                "ID",
                "Name",
                "Type",
                "Geometry",
                "Description",
                "Status",
                "Created At"
            ])

            for feature in features:

                writer.writerow([
                    feature.id,
                    feature.name,
                    feature.asset_type,
                    feature.geometry_type,
                    feature.description or "",
                    feature.status or "Active",
                    feature.created_at
                ])

    finally:
        db.close()

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(
        zip_buffer,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zip_file:

        for file_path in output_directory.iterdir():

            if file_path.is_file():

                zip_file.write(
                    file_path,
                    arcname=file_path.name
                )

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition":
                'attachment; filename="SpatioraMap_Export.zip"'
        }
    )