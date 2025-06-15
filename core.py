
import heapq
from collections import Counter
import time
import random
import string
import math
import pickle

class Node:
    def __init__(self, char=None, freq=0):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq

def build_huffman_tree(freq_map):
    heap = [Node(char, freq) for char, freq in freq_map.items()]
    heapq.heapify(heap)
    while len(heap) > 1:
        node1 = heapq.heappop(heap)
        node2 = heapq.heappop(heap)
        merged = Node(freq=node1.freq + node2.freq)
        merged.left = node1
        merged.right = node2
        heapq.heappush(heap, merged)
    return heap[0]

def build_codes(root):
    codes = {}
    def generate_code(node, current_code):
        if node is None: return
        if node.char is not None:
            codes[node.char] = current_code
        generate_code(node.left, current_code + "0")
        generate_code(node.right, current_code + "1")
    generate_code(root, "")
    return codes

def huffman_compress(text):
    freq_map = Counter(text)
    root = build_huffman_tree(freq_map)
    codes = build_codes(root)
    encoded_text = "".join(codes[char] for char in text)
    return encoded_text, root

def huffman_decompress(encoded_text, root):
    result = ""
    node = root
    for bit in encoded_text:
        node = node.left if bit == "0" else node.right
        if node.char is not None:
            result += node.char
            node = root
    return result

PI, E, PHI = 3.1415926535, 2.7182818284, 1.6180339887

def generate_key():
    current_time = time.strftime("%H:%M")
    time_number = int(current_time.split(":")[0]) * 60 + int(current_time.split(":")[1])
    trig_value = math.sin(time_number) + math.cos(time_number) * PI
    key_seed = int(abs(trig_value * E * PHI) * 1e6) % (10**6)
    random.seed(key_seed)
    characters = list(string.ascii_letters + string.digits + string.punctuation + " ")
    shuffled = characters[:]
    random.shuffle(shuffled)
    return dict(zip(characters, shuffled)), key_seed

def xor_encrypt(text, key_seed):
    return "".join(chr(ord(c) ^ int(PI * E * PHI * key_seed * (i + 1)) % 256) for i, c in enumerate(text))

def encrypt_message(text):
    sub_key, key_seed = generate_key()
    substituted = "".join(sub_key.get(c, c) for c in text)
    return xor_encrypt(substituted, key_seed), key_seed

def xor_decrypt(text, key_seed):
    return "".join(chr(ord(c) ^ int(PI * E * PHI * key_seed * (i + 1)) % 256) for i, c in enumerate(text))

def decrypt_message(encrypted, key_seed):
    decrypted_xor = xor_decrypt(encrypted, key_seed)
    sub_key, _ = generate_key()
    reverse_key = {v: k for k, v in sub_key.items()}
    return "".join(reverse_key.get(c, c) for c in decrypted_xor)