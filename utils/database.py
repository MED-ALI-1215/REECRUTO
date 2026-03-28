import chromadb
from chromadb.config import Settings
from datetime import datetime
import os

class CandidateDatabase:
    def __init__(self, db_path="./chroma_db"):
        """Initialize ChromaDB for candidate storage"""
        self.db_path = db_path
        
        # Create directory if it doesn't exist
        os.makedirs(db_path, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="candidates",
            metadata={"description": "CV candidates for job matching"}
        )
    
    def add_candidate(self, candidate_id, name, cv_text, structured_info="", file_name=""):
        """Add a candidate to the database"""
        try:
            self.collection.add(
                ids=[candidate_id],
                documents=[cv_text],
                metadatas=[{
                    "name": name,
                    "file_name": file_name,
                    "upload_date": datetime.now().isoformat(),
                    "structured_info": structured_info[:1000] if structured_info else ""  # Limit metadata size
                }]
            )
            return True
        except Exception as e:
            print(f"Error adding candidate: {str(e)}")
            return False
    
    def search_candidates(self, query, n_results=5):
        """Search for candidates matching a job description"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            return results
        except Exception as e:
            print(f"Error searching candidates: {str(e)}")
            return None
    
    def get_candidate_count(self):
        """Get total number of candidates in database"""
        try:
            return self.collection.count()
        except Exception as e:
            print(f"Error getting count: {str(e)}")
            return 0
    
    def get_all_candidates(self):
        """Get all candidates from the database"""
        try:
            count = self.collection.count()
            if count == 0:
                return {"ids": [], "metadatas": []}
            
            # Get all candidates
            results = self.collection.get()
            return results
        except Exception as e:
            print(f"Error getting all candidates: {str(e)}")
            return {"error": str(e)}
    
    def delete_candidate(self, candidate_id):
        """Delete a candidate from the database"""
        try:
            # First, verify the candidate exists
            existing = self.collection.get(ids=[candidate_id])
            if not existing or len(existing['ids']) == 0:
                raise Exception(f"Candidate {candidate_id} not found in database")
            
            print(f"Attempting to delete candidate: {candidate_id}")
            
            # Delete using ChromaDB's delete method
            self.collection.delete(ids=[candidate_id])
            
            # Verify deletion
            check = self.collection.get(ids=[candidate_id])
            if check and len(check['ids']) > 0:
                raise Exception(f"Candidate {candidate_id} still exists after delete attempt")
            
            print(f"Successfully deleted and verified removal of candidate: {candidate_id}")
            return True
            
        except Exception as e:
            error_msg = f"Error deleting candidate {candidate_id}: {str(e)}"
            print(error_msg)
            raise Exception(error_msg)
    
    def get_candidate_by_id(self, candidate_id):
        """Get a specific candidate by ID"""
        try:
            result = self.collection.get(ids=[candidate_id])
            if result and len(result['ids']) > 0:
                return {
                    'id': result['ids'][0],
                    'document': result['documents'][0],
                    'metadata': result['metadatas'][0]
                }
            return None
        except Exception as e:
            print(f"Error getting candidate: {str(e)}")
            return None
    
    def update_candidate(self, candidate_id, name=None, cv_text=None, structured_info=None):
        """Update candidate information"""
        try:
            # Get current candidate
            current = self.get_candidate_by_id(candidate_id)
            if not current:
                return False
            
            # Prepare updated data
            updated_metadata = current['metadata'].copy()
            if name:
                updated_metadata['name'] = name
            if structured_info:
                updated_metadata['structured_info'] = structured_info[:1000]
            
            updated_document = cv_text if cv_text else current['document']
            
            # Update by deleting and re-adding
            self.collection.delete(ids=[candidate_id])
            self.collection.add(
                ids=[candidate_id],
                documents=[updated_document],
                metadatas=[updated_metadata]
            )
            return True
        except Exception as e:
            print(f"Error updating candidate: {str(e)}")
            return False
    
    def clear_all(self):
        """Clear all candidates from the database (use with caution!)"""
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name="candidates")
            self.collection = self.client.get_or_create_collection(
                name="candidates",
                metadata={"description": "CV candidates for job matching"}
            )
            return True
        except Exception as e:
            print(f"Error clearing database: {str(e)}")
            return False