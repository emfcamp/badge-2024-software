class Partition:
    RUNNING = 1
    
    def __init__(self, which):
        pass
    
    def get_next_update(self):
        return self
    
    def into(self):
        return (1,2,3,4)
