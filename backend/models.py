from pydantic import BaseModel, Field 
from typing import List, Optional, Dict, Any

class QueryRequest(BaseModel):
    query:str
    top_k: Optional[int] = 5
    
class QueryResponse(BaseModel):
    results:List[dict]
    query:str 
    
class UploadResponse(BaseModel):
    message:str 
    file_name:str
    chunks_created:int 
    
    
