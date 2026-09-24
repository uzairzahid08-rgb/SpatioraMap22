from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel
from typing import Optional

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Feature

import json
import os
import tempfile
import zipfile
import csv

import shapefile


app = FastAPI(
    title="SpatioraMap",
    version="0.3.0"
)


# --------------------------------------------------
# FRONTEND
# --------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory="../frontend"),
    name="static"
)


@app.get("/")
def home():

    return FileResponse(
        "../frontend/index.html"
    )


# --------------------------------------------------
# PYDANTIC MODEL
# --------------------------------------------------

class FeatureData(BaseModel):

    geometry_type: str

    geometry: dict

    name: str

    asset_type: str

    description: Optional[str] = ""

    status: str = "Active"


# --------------------------------------------------
# CREATE FEATURE
# --------------------------------------------------

@app.post("/features")
def create_feature(
    feature_data: FeatureData
):

    allowed_types = [
        "Point",
        "LineString",
        "Polygon"
    ]

    if feature_data.geometry_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Invalid geometry type"
        )

    db: Session = SessionLocal()

    try:

        feature = Feature(

            geometry_type=
                feature_data.geometry_type,

            geometry=
                json.dumps(
                    feature_data.geometry
                ),

            name=
                feature_data.name,

            asset_type=
                feature_data.asset_type,

            description=
                feature_data.description,

            status=
                feature_data.status
        )

        db.add(feature)

        db.commit()

        db.refresh(feature)

        return {
            "message": "Feature saved successfully",
            "id": feature.id
        }

    finally:

        db.close()


# --------------------------------------------------
# GET ALL FEATURES
# --------------------------------------------------

@app.get("/features")
def get_features():

    db: Session = SessionLocal()

    try:

        features = (
            db.query(Feature)
            .order_by(
                Feature.id.desc()
            )
            .all()
        )

        result = []

        for feature in features:

            result.append({

                "id":
                    feature.id,

                "geometry_type":
                    feature.geometry_type,

                "geometry":
                    json.loads(
                        feature.geometry
                    ),

                "name":
                    feature.name,

                "asset_type":
                    feature.asset_type,

                "description":
                    feature.description,

                "status":
                    feature.status,

                "created_at":
                    feature.created_at
            })

        return result

    finally:

        db.close()


# --------------------------------------------------
# GET SINGLE FEATURE
# --------------------------------------------------

@app.get("/features/{feature_id}")
def get_feature(
    feature_id: int
):

    db: Session = SessionLocal()

    try:

        feature = (
            db.query(Feature)
            .filter(
                Feature.id == feature_id
            )
            .first()
        )

        if not feature:

            raise HTTPException(
                status_code=404,
                detail="Feature not found"
            )

        return {

            "id":
                feature.id,

            "geometry_type":
                feature.geometry_type,

            "geometry":
                json.loads(
                    feature.geometry
                ),

            "name":
                feature.name,

            "asset_type":
                feature.asset_type,

            "description":
                feature.description,

            "status":
                feature.status,

            "created_at":
                feature.created_at
        }

    finally:

        db.close()


# --------------------------------------------------
# UPDATE FEATURE
# --------------------------------------------------

@app.put("/features/{feature_id}")
def update_feature(
    feature_id: int,
    feature_data: FeatureData
):

    db: Session = SessionLocal()

    try:

        feature = (
            db.query(Feature)
            .filter(
                Feature.id == feature_id
            )
            .first()
        )

        if not feature:

            raise HTTPException(
                status_code=404,
                detail="Feature not found"
            )

        feature.geometry_type = (
            feature_data.geometry_type
        )

        feature.geometry = json.dumps(
            feature_data.geometry
        )

        feature.name = (
            feature_data.name
        )

        feature.asset_type = (
            feature_data.asset_type
        )

        feature.description = (
            feature_data.description
        )

        feature.status = (
            feature_data.status
        )

        db.commit()

        return {
            "message":
                "Feature updated successfully"
        }

    finally:

        db.close()


# --------------------------------------------------
# DELETE FEATURE
# --------------------------------------------------

@app.delete("/features/{feature_id}")
def delete_feature(
    feature_id: int
):

    db: Session = SessionLocal()

    try:

        feature = (
            db.query(Feature)
            .filter(
                Feature.id == feature_id
            )
            .first()
        )

        if not feature:

            raise HTTPException(
                status_code=404,
                detail="Feature not found"
            )

        db.delete(feature)

        db.commit()

        return {
            "message":
                "Feature deleted successfully"
        }

    finally:

        db.close()


# --------------------------------------------------
# STATISTICS
# --------------------------------------------------

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
            1
            for f in features
            if f.geometry_type == "Point"
        )

        lines = sum(
            1
            for f in features
            if f.geometry_type == "LineString"
        )

        polygons = sum(
            1
            for f in features
            if f.geometry_type == "Polygon"
        )

        active = sum(
            1
            for f in features
            if f.status == "Active"
        )

        inactive = sum(
            1
            for f in features
            if f.status == "Inactive"
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


# --------------------------------------------------
# DOWNLOAD SHAPEFILES + CSV
# --------------------------------------------------

@app.get("/download")
def download_data():

    db: Session = SessionLocal()

    try:

        features = (
            db.query(Feature)
            .order_by(
                Feature.id
            )
            .all()
        )

        if not features:

            raise HTTPException(
                status_code=404,
                detail="No features available for download"
            )

        temp_dir = tempfile.mkdtemp()

        # ------------------------------------------
        # CSV ATTRIBUTES
        # ------------------------------------------

        csv_file = os.path.join(
            temp_dir,
            "all_attributes.csv"
        )

        with open(
            csv_file,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "ID",
                "Name",
                "Asset_Type",
                "Description",
                "Status",
                "Geometry_Type",
                "Created_At"
            ])

            for feature in features:

                writer.writerow([

                    feature.id,

                    feature.name,

                    feature.asset_type,

                    feature.description or "",

                    feature.status,

                    feature.geometry_type,

                    feature.created_at
                ])


        # ------------------------------------------
        # CREATE SHAPEFILES BY GEOMETRY TYPE
        # ------------------------------------------

        geometry_groups = {

            "Point": [],

            "LineString": [],

            "Polygon": []
        }


        for feature in features:

            if feature.geometry_type in geometry_groups:

                geometry_groups[
                    feature.geometry_type
                ].append(feature)


        # ------------------------------------------
        # POINT SHAPEFILE
        # ------------------------------------------

        if geometry_groups["Point"]:

            shp_path = os.path.join(
                temp_dir,
                "points"
            )

            writer = shapefile.Writer(
                shp_path,
                shapeType=shapefile.POINT
            )

            writer.field(
                "ID",
                "N"
            )

            writer.field(
                "NAME",
                "C",
                size=100
            )

            writer.field(
                "TYPE",
                "C",
                size=100
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

            for feature in geometry_groups["Point"]:

                geometry = json.loads(
                    feature.geometry
                )

                coordinates = (
                    geometry["coordinates"]
                )

                writer.point(
                    coordinates[0],
                    coordinates[1]
                )

                writer.record(

                    feature.id,

                    feature.name,

                    feature.asset_type,

                    feature.description or "",

                    feature.status
                )

            writer.close()


        # ------------------------------------------
        # LINE SHAPEFILE
        # ------------------------------------------

        if geometry_groups["LineString"]:

            shp_path = os.path.join(
                temp_dir,
                "lines"
            )

            writer = shapefile.Writer(
                shp_path,
                shapeType=shapefile.POLYLINE
            )

            writer.field(
                "ID",
                "N"
            )

            writer.field(
                "NAME",
                "C",
                size=100
            )

            writer.field(
                "TYPE",
                "C",
                size=100
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

            for feature in geometry_groups["LineString"]:

                geometry = json.loads(
                    feature.geometry
                )

                coordinates = (
                    geometry["coordinates"]
                )

                writer.line([
                    coordinates
                ])

                writer.record(

                    feature.id,

                    feature.name,

                    feature.asset_type,

                    feature.description or "",

                    feature.status
                )

            writer.close()


        # ------------------------------------------
        # POLYGON SHAPEFILE
        # ------------------------------------------

        if geometry_groups["Polygon"]:

            shp_path = os.path.join(
                temp_dir,
                "polygons"
            )

            writer = shapefile.Writer(
                shp_path,
                shapeType=shapefile.POLYGON
            )

            writer.field(
                "ID",
                "N"
            )

            writer.field(
                "NAME",
                "C",
                size=100
            )

            writer.field(
                "TYPE",
                "C",
                size=100
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

            for feature in geometry_groups["Polygon"]:

                geometry = json.loads(
                    feature.geometry
                )

                coordinates = (
                    geometry["coordinates"]
                )

                writer.poly(
                    coordinates
                )

                writer.record(

                    feature.id,

                    feature.name,

                    feature.asset_type,

                    feature.description or "",

                    feature.status
                )

            writer.close()


        # ------------------------------------------
        # ZIP FILE
        # ------------------------------------------

        zip_path = os.path.join(
            temp_dir,
            "SpatioraMap_Export.zip"
        )

        with zipfile.ZipFile(
            zip_path,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zip_file:

            for filename in os.listdir(
                temp_dir
            ):

                full_path = os.path.join(
                    temp_dir,
                    filename
                )

                if filename != "SpatioraMap_Export.zip":

                    zip_file.write(
                        full_path,
                        filename
                    )


        return FileResponse(

            zip_path,

            media_type=
                "application/zip",

            filename=
                "SpatioraMap_Export.zip"
        )

    finally:

        db.close()