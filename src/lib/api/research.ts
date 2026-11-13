import { api } from "./client";
export type ImageAsset={id:string;original_filename:string;mime_type:string;file_size:number;width:number;height:number;sha256:string;created_at:string};
export type Research={id:string;title:string;image_id:string;subject_name:string|null;event_name:string|null;organization:string|null;status:string;created_at:string;updated_at:string;image:ImageAsset};
export type ResearchList={items:Research[];total:number;limit:number;offset:number};
export async function uploadImage(file:File){const body=new FormData();body.append("file",file);return api<ImageAsset>("/api/v1/images/upload",{method:"POST",body})}
export function createResearch(payload:Record<string,string>){return api<Research>("/api/v1/research",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)})}
export function getResearchList(){return api<ResearchList>("/api/v1/research?limit=50")}
export function getResearch(id:string){return api<Research>(`/api/v1/research/${encodeURIComponent(id)}`)}
