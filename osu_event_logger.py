import requests
import time
import copy 

GOSUMEMORY_URL = "http://localhost:24050/json"
POLL_INTERVAL = 0.05

def get_osu_data():
    """Attempts to fetch data from gosumemory."""
    try:
        response = requests.get(GOSUMEMORY_URL, timeout=0.1)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return None

def print_change(timestamp, event_type, details):
    """Formats and prints detected changes."""
    print(f"{timestamp:.3f} - {event_type}: {details}")

def main_loop():
    """Main data polling loop."""
    print("Script started. Waiting for data from gosumemory (osu! and gosumemory must be running)...")

    last_osu_state = -1
    prev_game_data = {}
    last_map_id = -1
    last_printed_accuracy = -1.0

    while True:
        current_time = time.time()
        data = get_osu_data()

        if data:
            menu_data = data.get('menu', {})
            current_osu_state = menu_data.get('state', -1)
            current_map_id = menu_data.get('bm', {}).get('metadata', {}).get('id', -1)
            if current_map_id == -1:
                 current_map_id = menu_data.get('bm', {}).get('id', -1)

            if current_osu_state == 2:
                gameplay_data = data.get('gameplay', {})
                if not gameplay_data:
                    time.sleep(POLL_INTERVAL)
                    continue

                if last_osu_state != 2 or not prev_game_data or current_map_id != last_map_id:
                    print(f"--- Game Started or Map Changed/Restarted (Map ID: {current_map_id}) ---")
                    prev_game_data = copy.deepcopy(gameplay_data)
                    last_map_id = current_map_id
                    last_printed_accuracy = -1.0
                    if 'hits' not in prev_game_data: prev_game_data['hits'] = {}
                    if 'combo' not in prev_game_data: prev_game_data['combo'] = {}
                    if 'hp' not in prev_game_data: prev_game_data['hp'] = {}
                else:
                    current_hits = gameplay_data.get('hits', {})
                    prev_hits = prev_game_data.get('hits', {})

                    if current_hits is None or prev_hits is None:
                         prev_game_data = copy.deepcopy(gameplay_data)
                         time.sleep(POLL_INTERVAL)
                         continue

                    hit_detected = False

       
                    if current_hits.get('300', 0) > prev_hits.get('300', 0):
                        print_change(current_time, "HIT", "300")
                        hit_detected = True
                    if current_hits.get('100', 0) > prev_hits.get('100', 0):
                        print_change(current_time, "HIT", "100")
                        hit_detected = True
                    if current_hits.get('50', 0) > prev_hits.get('50', 0):
                        print_change(current_time, "HIT", "50")
                        hit_detected = True
                    if current_hits.get('0', 0) > prev_hits.get('0', 0):
                        print_change(current_time, "HIT", "Miss") 
                        hit_detected = True
                        if gameplay_data.get('combo', {}).get('current', 0) == 0 and prev_game_data.get('combo', {}).get('current', 0) > 0:
                             print_change(current_time, "EVENT", f"Combo Break (was {prev_game_data.get('combo', {}).get('current', 0)})")
                    if current_hits.get('sliderBreaks', 0) > prev_hits.get('sliderBreaks', 0):
                        print_change(current_time, "EVENT", "Slider Break")
                        hit_detected = True
                        if gameplay_data.get('combo', {}).get('current', 0) == 0 and prev_game_data.get('combo', {}).get('current', 0) > 0:
                             print_change(current_time, "EVENT", f"Combo Break (was {prev_game_data.get('combo', {}).get('current', 0)})")

                    if hit_detected:
                        current_accuracy = gameplay_data.get('accuracy', 0.0)
                        if abs(current_accuracy - last_printed_accuracy) > 0.001:
                             print_change(current_time, "ACCURACY", f"{current_accuracy:.2f}%")
                             last_printed_accuracy = current_accuracy

                    current_hp = gameplay_data.get('hp', {}).get('current', 0)
                    prev_hp = prev_game_data.get('hp', {}).get('current', 0)
                    if current_hp < prev_hp:
                        print_change(current_time, "HP", f"Lost {prev_hp - current_hp:.0f} (Now: {current_hp:.0f})")
                    elif current_hp > prev_hp:
                         print_change(current_time, "HP", f"Gained {current_hp - prev_hp:.0f} (Now: {current_hp:.0f})")

                prev_game_data = copy.deepcopy(gameplay_data)

            elif last_osu_state == 2:
                print("--- Game Finished or Exited ---")
                final_game_data_to_use = prev_game_data

                if final_game_data_to_use:
                    final_accuracy = final_game_data_to_use.get('accuracy', 0.0)
                    final_score = final_game_data_to_use.get('score', 0)
                    final_combo_dict = final_game_data_to_use.get('combo', {})
                    final_max_combo = final_combo_dict.get('max', 0) if final_combo_dict else 0
                    final_hits = final_game_data_to_use.get('hits', {})

                    print(f"DEBUG: Final 'hits' data used: {final_hits}")

                    miss_count = final_hits.get('0', 0) if final_hits else 0 
                    sb_count = final_hits.get('sliderBreaks', 0) if final_hits else 0
                    h300 = final_hits.get('300',0) if final_hits else 0
                    h100 = final_hits.get('100',0) if final_hits else 0
                    h50 = final_hits.get('50',0) if final_hits else 0

                    print_change(time.time(), "FINAL SCORE", f"{final_score}")
                    print_change(time.time(), "FINAL ACCURACY", f"{final_accuracy:.2f}%")
                    print_change(time.time(), "FINAL MAX COMBO", f"{final_max_combo}")
                    print_change(time.time(), "FINAL HITS", f"300:{h300} 100:{h100} 50:{h50} Miss:{miss_count} SB:{sb_count}")
                else:
                     print("(!) No final gameplay data available (prev_game_data was empty).")

                prev_game_data = {}
                last_map_id = -1
                last_printed_accuracy = -1.0

            last_osu_state = current_osu_state

        else: 
            time.sleep(0.5)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\nScript stopped by user.")
    except Exception as e:
        import traceback
        print(f"\nAn unexpected error occurred: {e}")
        print(traceback.format_exc())