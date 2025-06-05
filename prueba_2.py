import numpy as np

x= [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
print(len(x))  # Output: 10
del x[:len(x) - 3]

print(x)  # Output: [8, 9, 10]
print(len(x))  # Output: 3