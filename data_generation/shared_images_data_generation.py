import argparse
import json
import random
import base64
import urllib.request
import itertools
import concurrent.futures
import time
import ssl
import string
import struct
import os
import tempfile
import shutil

def generate_random_image(width, height):
    """Generates a random BMP image and returns its base64 string."""
    row_size = (width * 3 + 3) & ~3
    pixel_data_size = row_size * height
    file_size = 54 + pixel_data_size
    
    # BMP Header (14 bytes) + DIB Header (40 bytes) = 54 bytesma
    header = struct.pack(
        '<2sIHHIIiiHHIIIIII',
        b'BM',          # Magic number (2s)
        file_size,      # File size (I)
        0, 0,           # Reserved (H, H)
        54,             # Offset to pixel data (I)
        40,             # Header size (I)
        width,          # Width (i)
        height,         # Height (i)
        1,              # Planes (H)
        24,             # Bits per pixel (H)
        0,              # Compression (I)
        pixel_data_size,# Image size (I)
        2835, 2835,     # Pixels per meter (I, I)
        0,              # Palette colors (I)
        0               # Important colors (I)
    )
    
    # Generate random pixels extremely fast using a single call to random.randbytes
    # The padding bytes at the end of each row can be random as well per BMP spec.
    pixels = random.randbytes(row_size * height)
        
    bmp_data = header + pixels
    return base64.b64encode(bmp_data).decode('utf-8')


# Define a corpus of words for prompt generation
word_corpus = [
    "the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog", "happy", "sad",
    "running", "swiftly", "through", "forest", "under", "bright", "sun", "shining",
    "stars", "moon", "night", "clear", "blue", "sky", "clouds", "floating", "gentle",
    "breeze", "blowing", "leaves", "trees", "whispering", "secrets", "river", "flowing",
    "ocean", "waves", "crashing", "sandy", "shore", "shell", "treasure", "hidden",
    "deep", "cave", "mountain", "climbing", "high", "peak", "snowy", "cold", "warm",
    "cozy", "fireplace", "crackling", "wood", "cabin", "peaceful", "valley", "green",
    "grass", "flowers", "blooming", "colorful", "garden", "butterfly", "fluttering",
    "bird", "singing", "sweet", "melody", "morning", "dew", "sparkling", "diamond",
    "golden", "light", "shadows", "dancing", "wall", "clock", "ticking", "time",
    "passing", "quietly", "silent", "thought", "dream", "adventure", "journey",
    "map", "compass", "path", "winding", "road", "city", "lights", "bustling", "streets",
    "ancient", "bridge", "castle", "kingdom", "shadow", "whisper", "echo", "thunder",
    "lightning", "storm", "rain", "puddle", "rainbow", "foggy", "misty", "drizzle",
    "glowing", "ember", "flame", "smoke", "ash", "dust", "windy", "stormy", "tempest",
    "tornado", "hurricane", "blizzard", "desert", "dune", "cactus", "oasis", "mirage",
    "canyon", "cliff", "ravine", "waterfall", "lake", "pond", "stream", "creek",
    "meadow", "pasture", "field", "forest", "jungle", "swamp", "marsh", "bog",
    "tundra", "glacier", "iceberg", "snowflake", "frosty", "chilly", "breezy", "gusty",
    "sunny", "cloudy", "overcast", "gloomy", "cheerful", "joyful", "playful", "merry",
    "lively", "energetic", "calm", "serene", "tranquil", "placid", "still", "quiet",
    "noisy", "loud", "clamorous", "gentle", "soft", "smooth", "rough", "rugged",
    "steep", "flat", "level", "wide", "broad", "narrow", "tight", "loose",
    "heavy", "light", "swift", "slow", "rapid", "quick", "speedy", "leisurely"
]

def generate_random_sentence():
    length = random.randint(10, 25)
    words = random.choices(word_corpus, k=length)
    return " ".join(words).capitalize() + "."

def main():
    parser = argparse.ArgumentParser(description="Generate a visual LLM benchmark dataset with shared (but not necessarily prefix) images.")
    parser.add_argument("--shared_ratio", type=float, default=2.0, help="Number of times each image is shared across requests.")
    parser.add_argument("--output_file", type=str, default="shared_images_benchmark.jsonl", help="Path to save the JSONL file")
    parser.add_argument("--duration", type=int, default=30, help="Duration of the benchmark in seconds")
    parser.add_argument("--rps", type=int, default=10, help="Requests per second")
    parser.add_argument("--resolution", type=str, choices=["180p", "360p", "720p", "1080p"], default="360p")
    parser.add_argument("--max_tokens", type=int, default=1, help="Max output tokens")
    parser.add_argument("--model", type=str, default="qwen/Qwen2.5-VL-7B-Instruct", help="Model name")
    parser.add_argument("--warmup", type=int, default=10, help="Number of warmup requests to send (default: 10)")

    args = parser.parse_args()

    resolution_map = {
        "180p": (320, 180),
        "360p": (640, 360),
        "720p": (1280, 720),
        "1080p": (1920, 1080)
    }
    width, height = resolution_map[args.resolution]
    total_requests = args.duration * args.rps
    
    # Determine how many unique images we need
    num_unique_images = max(1, int(total_requests / args.shared_ratio))
    print(f"Generating {num_unique_images} unique random images in memory...")
    
    print(f"Starting concurrent generation with ThreadPoolExecutor...")
    unique_images = [None] * num_unique_images
    def generate_and_store_image(image_idx):
        unique_images[image_idx] = generate_random_image(width, height)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(generate_and_store_image, idx) for idx in range(num_unique_images)]
        for progress_idx, future in enumerate(concurrent.futures.as_completed(futures)):
            future.result()
            if (progress_idx + 1) % max(1, num_unique_images // 10) == 0 or progress_idx == num_unique_images - 1:
                print(f"Generated {progress_idx + 1}/{num_unique_images} images concurrently...")

    warmup_requests = []
    
    # --- GENERATE WARM-UP REQUESTS ---
    print(f"Generating {args.warmup} warm-up requests...")
    for _ in range(args.warmup):
        sentence = generate_random_sentence()
        components = [{"type": "text", "text": sentence}]

        warmup_requests.append({
            "model": args.model,
            "messages": [{"role": "user", "content": components}],
            "max_tokens": args.max_tokens,
            "temperature": 0.7
        })
    all_images = unique_images * int(args.shared_ratio)
    
    random.shuffle(all_images)

    main_requests = []
    num_requests = args.duration * args.rps
    for i in range(num_requests):            
        sentence = generate_random_sentence()
        # Store request metadata with the image index to keep memory extremely low
        main_requests.append({
            "sentence": sentence,
            "image_index": i % num_unique_images
        })

    # Shuffle the requests - since they don't contain the heavy image payloads, this is extremely fast and memory-efficient
    random.shuffle(main_requests)
    
    print(f"Writing requests incrementally to '{args.output_file}'...")
    with open(args.output_file, "w", encoding="utf-8") as f:
        # Write warm-up requests first
        for req in warmup_requests:
            f.write(json.dumps(req) + "\n")
            
        # Load images from memory and write the main requests
        for idx, req_meta in enumerate(main_requests):
            img_base64 = unique_images[req_meta["image_index"]]
            
            components = [
                {"type": "text", "text": req_meta["sentence"]},
                {"type": "image_url", "image_url": {"url": f"data:image/bmp;base64,{img_base64}"}}
            ]
            
            request = {
                "model": args.model,
                "messages": [{"role": "user", "content": components}],
                "max_tokens": args.max_tokens,
                "temperature": 0.7
            }
            f.write(json.dumps(request) + "\n")
            
            if (idx + 1) % max(1, num_requests // 10) == 0 or idx == num_requests - 1:
                print(f"Wrote {idx + 1}/{num_requests} main requests...")

    print(f"Successfully saved {args.warmup + num_requests} total requests ({args.warmup} warm-up + {num_requests} main) to '{args.output_file}'.")

if __name__ == "__main__":
    main()
