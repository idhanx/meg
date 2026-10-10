"""The only intended config writer; never imported by reviewer modules."""
class Promoter:
    def promote(self,*_):
        raise NotImplementedError("requires gatekeeper persistence")
