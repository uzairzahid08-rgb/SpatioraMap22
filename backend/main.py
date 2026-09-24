from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime
import json
import csv
import io
import zipfile
import tempfile
import shapefile

from backend.database import SessionLocal, engine
from backend.models import Base, Feature


# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------

Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# APP
# ---------------------------------------------------------

app = FastAPI(
    title="SpatioraMap",
    version="0.4.0"
)


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


# ---------------------------------------------------------
# PYDANTIC MODEL
# ---------------------------------------------------------

class FeatureData(BaseModel):
    geometry_type: str
    geometry: dict
    name: str
    asset_type: str
    description: Optional[str] = ""
    status: str = "Active"


# ---------------------------------------------------------
# ROOT
# ---------------------------------------------------------

@app.get("/")
def home():

    index_file = FRONTEND_DIR / "index.html"

    if not index_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Frontend index.html not found."
        )

    return FileResponse(index_file)


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "ok",
        "application": "SpatioraMap"
    }


# ---------------------------------------------------------
# CREATE FEATURE
# ---------------------------------------------------------

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

    if not data.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Feature name is required."
        )

    db: Session = SessionLocal()

    try:

        feature = Feature(
            geometry_type=data.geometry_type,
            geometry=json.dumps(data.geometry),
            name=data.name.strip(),
            asset_type=data.asset_type.strip(),
            description=(
                data.description.strip()
                if data.description
                else ""
            ),
            status=data.status,
            created_at=datetime.utcnow()
        )

        db.add(feature)
        db.commit()
        db.refresh(feature)

        return {
            "id": feature.id,
            "geometry_type": feature.geometry_type,
            "geometry": json.loads(feature.geometry),
            "name": feature.name,
            "asset_type": feature.asset_type,
            "description": feature.description,
            "status": feature.status,
            "created_at": feature.created_at
        }

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Error saving feature: {str(e)}"
        )

    finally:
        db.close()


# ---------------------------------------------------------
# GET ALL FEATURES
# ---------------------------------------------------------

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
                "status": feature.status,
                "created_at": feature.created_at
            })

        return result

    finally:
        db.close()


# ---------------------------------------------------------
# GET SINGLE FEATURE
# ---------------------------------------------------------

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
            "status": feature.status,
            "created_at": feature.created_at
        }

    finally:
        db.close()


# ---------------------------------------------------------
# UPDATE FEATURE
# ---------------------------------------------------------

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

    if not data.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Feature name is required."
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
        feature.name = data.name.strip()
        feature.asset_type = data.asset_type.strip()
        feature.description = (
            data.description.strip()
            if data.description
            else ""
        )
        feature.status = data.status

        db.commit()
        db.refresh(feature)

        return {
            "id": feature.id,
            "geometry_type": feature.geometry_type,
            "geometry": json.loads(feature.geometry),
            "name": feature.name,
            "asset_type": feature.asset_type,
            "description": feature.description,
            "status": feature.status,
            "created_at": feature.created_at
        }

    except HTTPException:

        db.rollback()
        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Error updating feature: {str(e)}"
        )

    finally:
        db.close()


# ---------------------------------------------------------
# DELETE FEATURE
# ---------------------------------------------------------

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
            "message": "Feature deleted successfully.",
            "id": feature_id
        }

    except HTTPException:

        db.rollback()
        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Error deleting feature: {str(e)}"
        )

    finally:
        db.close()


# ---------------------------------------------------------
# STATISTICS
# ---------------------------------------------------------

@app.get("/statistics")
def statistics():

    db: Session = SessionLocal()

    try:

        features = db.query(Feature).all()

        total = len(features)
        points = 0
        lines = 0
        polygons = 0
        active = 0
        inactive = 0

        for feature in features:

            if feature.geometry_type == "Point":
                points += 1

            elif feature.geometry_type == "LineString":
                lines += 1

            elif feature.geometry_type == "Polygon":
                polygons += 1

            if feature.status == "Active":
                active += 1

            elif feature.status == "Inactive":
                inactive += 1

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


# ---------------------------------------------------------
# DOWNLOAD SHAPEFILES + ATTRIBUTES
# ---------------------------------------------------------

@app.get("/download")
def download_data():

    db: Session = SessionLocal()

    try:

        features = (
            db.query(Feature)
            .order_by(Feature.id.asc())
            .all()
        )

        if not features:
            raise HTTPException(
                status_code=404,
                detail="No features available for download."
            )

        temp_dir = Path(tempfile.mkdtemp())

        point_features = []
        line_features = []
        polygon_features = []

        attributes = []

        for feature in features:

            geometry = json.loads(feature.geometry)

            record = {
                "id": feature.id,
                "name": feature.name,
                "asset_type": feature.asset_type,
                "description": feature.description or "",
                "status": feature.status,
                "geometry_type": feature.geometry_type,
                "created_at": str(feature.created_at)
            }

            attributes.append(record)

            if feature.geometry_type == "Point":
                point_features.append(
                    (geometry, record)
                )

            elif feature.geometry_type == "LineString":
                line_features.append(
                    (geometry, record)
                )

            elif feature.geometry_type == "Polygon":
                polygon_features.append(
                    (geometry, record)
                )

        def write_shapefile(
            geometry_type,
            feature_list,
            output_name
        ):

            if not feature_list:
                return None

            shp_path = temp_dir / output_name

            if geometry_type == "Point":

                writer = shapefile.Writer(
                    str(shp_path),
                    shapeType=shapefile.POINT
                )

            elif geometry_type == "LineString":

                writer = shapefile.Writer(
                    str(shp_path),
                    shapeType=shapefile.POLYLINE
                )

            elif geometry_type == "Polygon":

                writer = shapefile.Writer(
                    str(shp_path),
                    shapeType=shapefile.POLYGON
                )

            writer.field(
                "ID",
                "N"
            )

            writer.field(
                "NAME",
                "C",
                size=150
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
                size=30
            )

            writer.field(
                "CREATED",
                "C",
                size=50
            )

            for geometry, record in feature_list:

                coordinates = geometry.get(
                    "coordinates"
                )

                if geometry_type == "Point":

                    writer.point(
                        coordinates[0],
                        coordinates[1]
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
                    record["id"],
                    record["name"],
                    record["asset_type"],
                    record["description"],
                    record["status"],
                    record["created_at"]
                )

            writer.close()

            return shp_path

        write_shapefile(
            "Point",
            point_features,
            "points"
        )

        write_shapefile(
            "LineString",
            line_features,
            "lines"
        )

        write_shapefile(
            "Polygon",
            polygon_features,
            "polygons"
        )

        csv_path = temp_dir / "all_attributes.csv"

        with open(
            csv_path,
            "w",
            newline="",
            encoding="utf-8"
        ) as csv_file:

            writer = csv.DictWriter(
                csv_file,
                fieldnames=[
                    "id",
                    "name",
                    "asset_type",
                    "description",
                    "status",
                    "geometry_type",
                    "created_at"
                ]
            )

            writer.writeheader()
            writer.writerows(attributes)

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(
            zip_buffer,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zip_file:

            for file_path in temp_dir.iterdir():

                if file_path.is_file():

                    zip_file.write(
                        file_path,
                        arcname=file_path.name
                    )

        zip_buffer.seek(0)

        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition":
                    'attachment; filename="SpatioraMap_Export.zip"'
            }
        )

    finally:
        db.close()