"""Reusable voice profiles and samples, scoped like project characters."""
import base64
import json
import os
import threading
import time
import uuid
import contextlib
from pathlib import Path
from typing import Literal
import requests
from pydantic import BaseModel,ConfigDict,Field
from . import runtime as eb, media as quality, providers

def store(): return eb.workspace_dir()/"voices.json"
_lock=threading.RLock()
API="https://api.elevenlabs.io/v1"
_config_cache=None


class VoiceSettings(BaseModel):
    model_config=ConfigDict(extra="forbid")
    stability: Literal[0.0,0.5,1.0] = 1.0
    similarity_boost: float = Field(default=.8,ge=0,le=1,allow_inf_nan=False)
    speed: float = Field(default=1,ge=.7,le=1.2,allow_inf_nan=False)


class DesignReq(BaseModel):
    model_config=ConfigDict(extra="forbid")
    project_id: str
    description: str = Field(min_length=20,max_length=1000)
    text: str = Field(min_length=100,max_length=1000)
    seed: int = Field(default=1377,ge=0,le=2147483647,strict=True)


class SaveReq(BaseModel):
    model_config=ConfigDict(extra="forbid")
    project_id: str
    id: str | None = None
    name: str = Field(min_length=1,max_length=80)
    description: str = Field(default="",max_length=1000)
    preview_asset_id: str | None = None
    provider_voice_id: str | None = None
    public_owner_id: str | None = None
    language_code: str | None = Field(default=None,max_length=12)
    settings: VoiceSettings = Field(default_factory=VoiceSettings)
    seed: int = Field(default=1377,ge=0,le=4294967295,strict=True)


class CloneReq(BaseModel):
    model_config=ConfigDict(extra="forbid")
    project_id: str
    name: str = Field(min_length=1,max_length=80)
    description: str = Field(default="",max_length=1000)
    asset_ids: list[str] = Field(min_length=1,max_length=5)
    consent: bool = False
    remove_background_noise: bool = False
    language_code: str | None = Field(default=None,max_length=12)


def _load():return json.loads(store().read_text()) if store().exists() else {}
def _save(data):
    store().parent.mkdir(parents=True,exist_ok=True);temp=store().with_suffix(".tmp");temp.write_text(json.dumps(data,indent=1));temp.replace(store())
def list_for(pid):return [v for v in _load().values() if v["project_id"]==pid and not v.get("deleted_at")]
def get_for(pid,vid):
    voice=_load().get(vid)
    if not voice or voice["project_id"]!=pid or voice.get("deleted_at"):raise ValueError("That saved voice is unavailable in this project.")
    return voice


def refresh_status(pid,vid):
    with _lock:
        voice=get_for(pid,vid)
        status=_request("GET","/voices/"+voice["voice_id"]).json().get("voice_verification") or {}
        if status.get("is_verified") is True or status.get("requires_verification") is False:
            voice["requires_verification"]=False
        elif status.get("requires_verification") is True:voice["requires_verification"]=True
        data=_load();data[vid]=voice;_save(data);return voice


def _request(method,path,**kwargs):
    if not providers.ready('elevenlabs'):
        raise ValueError('Add your ElevenLabs key in Connections to design, clone, or save voices.')
    return providers.request('elevenlabs', method, path, **kwargs)



def design(req):
    if len(req.description.strip())<20 or len(req.text.strip())<100:raise ValueError("Add a voice description and at least 100 characters of sample dialogue.")
    r=_request("POST","/text-to-voice/design",params={"output_format":"mp3_44100_128"},json={
        "voice_description":req.description.strip(),"text":req.text.strip(),"model_id":"eleven_ttv_v3","seed":req.seed,"stream_previews":False})
    data=r.json();previews=data.get("previews",[])
    if not previews:raise ValueError("The provider returned no voice samples.")
    total=round(len(req.text.strip())*.0003,4);results=[]
    for index,p in enumerate(previews):
        path=eb.MEDIA/f"{uuid.uuid4().hex[:12]}.mp3";path.write_bytes(base64.b64decode(p["audio_base_64"],validate=True))
        duration=quality.probe(str(path))["duration"]
        if duration<=0:raise ValueError("The provider returned an unreadable voice sample.")
        results.append({"url":f"/media/{path.name}","label":f"Voice sample {index+1}","cost_usd":round(total/len(previews),4),
          "generated_voice_id":p["generated_voice_id"],"voice_description":req.description,"sample_text":data.get("text",req.text),
          "duration":duration,"source":"voice-design","cost_is_estimate":True,"design_seed":req.seed})
    return results


def save(req,project):
    if req.project_id!=project["id"] or not req.name.strip():raise ValueError("Give the voice a name in the current project.")
    validate_language(req.language_code)
    with _lock:
        data=_load();old=get_for(req.project_id,req.id) if req.id else None
        preview=next((a for a in project["assets"] if a["id"]==req.preview_asset_id and a.get("source")=="voice-design"),None)
        if old:voice=dict(old)
        elif req.preview_asset_id:
            if not preview or not preview.get("generated_voice_id"):raise ValueError("Choose a generated voice sample from this project.")
            existing=next((v for v in data.values() if v["project_id"]==req.project_id and v.get("preview_asset_id")==req.preview_asset_id),None)
            if existing:voice=dict(existing)
            else:
                result=_request("POST","/text-to-voice",json={"voice_name":req.name.strip(),"voice_description":req.description or preview["voice_description"],"generated_voice_id":preview["generated_voice_id"]}).json()
                voice={"voice_id":result["voice_id"],"preview_url":preview["url"],"preview_asset_id":preview["id"],"origin":"designed"}
        elif req.provider_voice_id:
            if not re_voice_id(req.provider_voice_id):raise ValueError("Choose a valid voice.")
            selected_id=req.provider_voice_id
            if req.public_owner_id:
                if not re_voice_id(req.public_owner_id):raise ValueError("Choose a valid library voice.")
                selected_id=_request("POST",f'/voices/add/{req.public_owner_id}/{selected_id}',json={"new_name":req.name.strip()}).json()["voice_id"]
            result=_request("GET","/voices/"+selected_id).json()
            voice={"voice_id":result["voice_id"],"preview_url":result.get("preview_url"),"origin":"library"}
        else:raise ValueError("Generate a sample or select a library voice first.")
        voice.update(id=voice.get("id") or uuid.uuid4().hex[:12],project_id=req.project_id,name=req.name.strip(),
                     description=req.description.strip(),settings=req.settings.model_dump(),seed=req.seed,model="eleven_v3",language_code=req.language_code,updated=time.time())
        voice.setdefault("created",time.time());data[voice["id"]]=voice;_save(data);return voice


def re_voice_id(value):
    import re
    return bool(re.fullmatch(r"[\w-]{1,100}",value))


def speak(text,profile,with_timestamps=False):
    if profile.get("requires_verification"):raise ValueError("This cloned voice needs verification in ElevenLabs before it can be used.")
    if not text.strip() or len(text)>5000:raise ValueError("Eleven v3 accepts 1–5,000 characters per speech clip. Split longer narration into scenes.")
    payload={"text":text,"model_id":profile.get("model","eleven_v3"),"seed":profile.get("seed",1377),
             "voice_settings":VoiceSettings.model_validate(profile.get("settings",{})).model_dump()}
    if profile.get("language_code"):payload["language_code"]=profile["language_code"]
    r=_request("POST",f'/text-to-speech/{profile["voice_id"]}'+('/with-timestamps' if with_timestamps else ''),params={"output_format":"mp3_44100_128"},json=payload)
    timing=r.json() if with_timestamps else {}
    path=eb.MEDIA/f"{uuid.uuid4().hex[:12]}.mp3";path.write_bytes(base64.b64decode(timing['audio_base64'],validate=True) if with_timestamps else r.content)
    duration=quality.probe(str(path))["duration"]
    if duration<=0:raise ValueError("The voice provider returned an unreadable audio clip.")
    return {"url":f"/media/{path.name}","label":profile["name"]+" · voice","duration":duration,"cost_usd":round(len(text)*.0003,4),
            "voice_profile_id":profile.get("id"),"voice_id":profile["voice_id"],"voice_settings":payload["voice_settings"],"seed":payload["seed"],"cost_is_estimate":True,
            "alignment":timing.get('normalized_alignment') or timing.get('alignment')}


def config():
    model=next((m for m in _request("GET","/models").json() if m["model_id"]=="eleven_v3"),None)
    if not model:raise ValueError("Eleven v3 is not available on the connected account.")
    data={"model_id":"eleven_v3","name":model.get("name") or "Eleven v3","languages":model.get("languages",[]),
          "max_characters":min(5000,model.get("maximum_text_length_per_request") or 5000)}
    return data


def validate_language(code):
    if code and code not in {l["language_id"] for l in config()["languages"]}:raise ValueError("Choose a language supported by Eleven v3.")


def library(search="",language="",page=0):
    validate_language(language)
    params={"page_size":30,"page":max(0,min(int(page),1000)),"sort":"usage_character_count_1y","include_custom_rates":"false"}
    if search:params["search"]=search[:100]
    if language:params["language"]=language
    data=_request("GET","/shared-voices",params=params).json()
    return {"voices":[{"id":v["voice_id"],"name":v.get("name","Voice")[:80],"description":(v.get("description") or "")[:1000],
        "preview_url":v.get("preview_url"),"public_owner_id":v.get("public_owner_id"),"language":v.get("language"),"accent":v.get("accent"),
        "verified_languages":v.get("verified_languages",[])} for v in data.get("voices",[])],"next_page":page+1 if data.get("has_more") else None}


def clone_inputs(req,project):
    if req.project_id!=project["id"] or not req.name.strip():raise ValueError("Give this voice a name in the current project.")
    if not req.consent:raise ValueError("Confirm that this is your voice or you have permission to use it.")
    validate_language(req.language_code);paths=[];duration=0
    for aid in dict.fromkeys(req.asset_ids):
        asset=next((a for a in project["assets"] if a["id"]==aid and a["kind"] in ("audio","video")),None)
        if not asset:raise ValueError("Choose recordings from this project.")
        path=Path(eb.local_path(asset["url"]))
        if not path.is_file() or path.stat().st_size>20_000_000:raise ValueError("Each voice recording must be smaller than 20 MB.")
        info=quality.probe(str(path))
        if not info["has_audio"] or info["duration"]<=0:raise ValueError("A selected file contains no readable audio.")
        duration+=info["duration"];paths.append(path)
    if duration<10 or duration>600:raise ValueError("Use 10 seconds to 10 minutes of clear speech for this voice.")
    return paths


def clone(req,project):
    paths=clone_inputs(req,project)
    with _lock:
        data=_load()
        existing=next((v for v in data.values() if v["project_id"]==req.project_id and v.get("clone_asset_ids")==req.asset_ids and v["name"]==req.name.strip()),None)
        if existing:return existing
        with contextlib.ExitStack() as stack:
            files=[("files",(path.name,stack.enter_context(path.open("rb")),"application/octet-stream")) for path in paths]
            result=_request("POST","/voices/add",data={"name":req.name.strip(),"description":req.description,"remove_background_noise":str(req.remove_background_noise).lower()},files=files).json()
        voice={"id":uuid.uuid4().hex[:12],"project_id":req.project_id,"voice_id":result["voice_id"],"name":req.name.strip(),"description":req.description,
            "origin":"cloned","clone_asset_ids":req.asset_ids,"preview_url":project["assets"][next(i for i,a in enumerate(project["assets"]) if a["id"]==req.asset_ids[0])]["url"],
            "requires_verification":bool(result.get("requires_verification")),"settings":VoiceSettings().model_dump(),"seed":1377,"model":"eleven_v3",
            "language_code":req.language_code,"consent_recorded_at":time.time(),"created":time.time(),"updated":time.time()}
        data[voice["id"]]=voice;_save(data);return voice
