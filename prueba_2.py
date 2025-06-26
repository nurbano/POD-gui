import numpy as np
VALUES=[]
x= [(1, 2, 3), (4, 5, 6), (7, 8, 9), (10,11, 12)    ]
data="1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0"
for i in range(10):
    values = list(map(float, data.split(',')))
    values.insert(0, str(i))
    VALUES.append(values)


print(VALUES[-2])