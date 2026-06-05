from fastapi import FastAPI, HTTPException, Depends, Header, Body
from pydantic import BaseModel
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

# ------------------- การตั้งค่า -------------------
app = FastAPI(title="VIDER TRAK", version="1.1.0")

UNLOCK_CODE = "SC.Thanva"
ALLOWED_PLATFORMS = ["microsoft", "genai"]
MASTER_SECRET = "VIDER-TRAK-ROOT-2026"

TRAK_CURRENT_STATE = {"active": False, "current_mission": None, "progress": []}
TRAK_MEMORY = {"history": [], "total_records": 0}
API_KEYS = {}

# ------------------- โครงสร้างข้อมูล -------------------
class MissionRequest(BaseModel):
    goal: str
    context: Optional[str] = ""
    language: Optional[str] = "fr"

class UnlockRequest(BaseModel):
    unlock_code: str
    platform: str

# ------------------- ตรวจสอบสิทธิ์ -------------------
def verify_access(authorization: Optional[str] = Header(None),
                  x_unlock: Optional[str] = Header(None),
                  x_platform: Optional[str] = Header(None)):
    if x_unlock == UNLOCK_CODE and x_platform and x_platform.lower() in ALLOWED_PLATFORMS:
        return {"type": "unlocked", "platform": x_platform}
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "ต้องมีคีย์หรือรหัสปลดล็อก")
    key = authorization.split(" ")[1]
    if key not in API_KEYS or not API_KEYS[key]["active"]:
        raise HTTPException(403, "คีย์ไม่ถูกต้อง")
    return {"type": "standard"}

# ------------------- API -------------------
@app.post("/api/unlock")
def unlock(req: UnlockRequest):
    if req.unlock_code == UNLOCK_CODE and req.platform.lower() in ALLOWED_PLATFORMS:
        return {"status": "unlocked", "message": "ใช้งานได้ไม่ต้องมีคีย์"}
    raise HTTPException(403, "รหัสหรือแพลตฟอร์มไม่ถูกต้อง")

@app.post("/api/create-key")
def create_key(secret: str = Header(..., alias="X-Master-Secret")):
    if secret != MASTER_SECRET:
        raise HTTPException(403, "ไม่มีสิทธิ์")
    key = f"VIDER-{uuid.uuid4().hex[:16].upper()}"
    API_KEYS[key] = {"active": True, "expires": None}
    return {"api_key": key}

@app.post("/mission/start")
def start(mission: MissionRequest, access: Dict = Depends(verify_access)):
    TRAK_CURRENT_STATE.update({
        "active": True, "current_mission": mission.goal, "progress": []
    })
    return {"status": "started", "mission": mission.goal}

@app.post("/mission/evaluate")
def evaluate(situation: str = Body(...), options: List[str] = Body(...), access: Dict = Depends(verify_access)):
    scores = {opt: round(0.5 + (0.2 if opt in TRAK_MEMORY.get("success", []) else 0), 2) for opt in options}
    best = max(scores, key=scores.get)
    TRAK_CURRENT_STATE["progress"].append({"situation": situation, "selected": best})
    return {"selected": best, "confidence": scores[best]}

@app.post("/mission/complete")
def complete(success: bool = Body(True), access: Dict = Depends(verify_access)):
    TRAK_MEMORY["history"].append(TRAK_CURRENT_STATE)
    TRAK_MEMORY["total_records"] += 1
    TRAK_CURRENT_STATE.update({"active": False, "current_mission": None})
    return {"status": "completed"}

@app.get("/info")
def info():
    return {
        "name": "VIDER TRAK",
        "feature": "ตัดสินใจเก่ง ประเมินตรงจุด",
        "special_unlock": {"code": UNLOCK_CODE, "platforms": ALLOWED_PLATFORMS}
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 VIDER TRAK พร้อมใช้งาน | ปลดล็อก: SC.Thanva")
    uvicorn.run(app, host="0.0.0.0", port=8000)
