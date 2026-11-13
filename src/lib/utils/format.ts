export const dateFormat=(s:string)=>new Intl.DateTimeFormat(undefined,{dateStyle:"medium"}).format(new Date(s));
export const sizeFormat=(n:number)=>n<1024*1024?`${(n/1024).toFixed(0)} KB`:`${(n/1024/1024).toFixed(2)} MB`;
