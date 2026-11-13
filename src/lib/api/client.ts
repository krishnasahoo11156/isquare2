const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export class ApiError extends Error { constructor(message:string, public status:number){super(message)} }
export async function api<T>(path:string, init?:RequestInit):Promise<T>{ let res:Response; try{res=await fetch(`${base}${path}`,init)}catch{throw new ApiError("Could not reach the iSquare service. Check that the backend is running.",0)} if(!res.ok){let msg="The request could not be completed.";try{const data=await res.json();msg=data.detail?.message||msg}catch{}throw new ApiError(msg,res.status)}return res.json() }
