

def milliseconds_to_hhmmss(milliseconds):
    seconds = int((milliseconds / 1000) % 60)
    minutes = int((milliseconds / (1000 * 60)) % 60)
    hours = int((milliseconds / (1000 * 60 * 60)) % 24)

    # Format the result as hh:mm:ss
    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return time_str