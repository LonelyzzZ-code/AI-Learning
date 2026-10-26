import faiss
import numpy as np

d = 2048
index = faiss.IndexFlatL2(d)
all_vectors = np.random.rand(3,d)
vecs = np.array(all_vectors,dtype = "float32")
faiss.normalize_L2(vecs)
index.add(vecs)

q_vec = np.random.rand(1, d).astype("float32")
faiss.normalize_L2(q_vec)
D,I = index.search(q_vec,k = 2)
print("下标：",I)
print("距离：",D)