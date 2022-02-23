import torch

some_global_var = 10

def capture(*args, **kwargs):
    def decorator():
        pass


#@torch.jit.script
class Test:
    def __init__(self, x: int, kwg: int =10):
        self.x = x

#t = torch.jit.script(Test(10))
#print(type(t))


if __name__ == "__main__":
    pass