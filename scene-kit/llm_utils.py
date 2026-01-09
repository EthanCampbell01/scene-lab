import os, json, time, requests

def _strip_json(text: str) -> str:
    text = text.strip()
    # remove markdown fences if present
    if text.startswith('```'):
        text = text.split('```',2)[1] if '```' in text else text
    # try to locate first { and last }
    a = text.find('{')
    b = text.rfind('}')
    if a != -1 and b != -1 and b > a:
        return text[a:b+1]
    return text

def call_openrouter(system: str, user: str, temperature: float = 0.4, model: str | None = None) -> str:
    key = os.getenv('OPENROUTER_API_KEY')
    if not key:
        raise RuntimeError('OPENROUTER_API_KEY not set')
    model = model or os.getenv('OPENROUTER_MODEL','anthropic/claude-3.5-sonnet')
    url = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type':'application/json',
        'HTTP-Referer': 'https://localhost/scene-kit',
        'X-Title': 'Scene Kit'
    }
    data = {
        'model': model,
        'messages': [{'role':'system','content':system},{'role':'user','content':user}],
        'temperature': float(os.getenv('OPENROUTER_TEMPERATURE', str(temperature)))
    }
    r = requests.post(url, headers=headers, json=data, timeout=120)
    r.raise_for_status()
    return r.json()['choices'][0]['message']['content']

def call_ollama(system: str, user: str, temperature: float = 0.4, model: str | None = None, host: str | None = None) -> str:
    host = host or os.getenv('OLLAMA_HOST','http://localhost:11434')
    model = model or os.getenv('OLLAMA_MODEL','llama3.1:8b')
    # try chat API
    url = host.rstrip('/') + '/api/chat'
    payload = {
        'model': model,
        'messages': [{'role':'system','content':system},{'role':'user','content':user}],
        'options': {'temperature': float(os.getenv('OLLAMA_TEMPERATURE', str(temperature)))},
        'stream': False
    }
    r = requests.post(url, json=payload, timeout=120)
    if r.status_code == 404:
        url = host.rstrip('/') + '/api/generate'
        payload = {
            'model': model,
            'prompt': system + '\n\n' + user,
            'options': {'temperature': float(os.getenv('OLLAMA_TEMPERATURE', str(temperature)))},
            'stream': False
        }
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        return r.json().get('response','')
    r.raise_for_status()
    return r.json().get('message',{}).get('content','')

def run_llm(provider: str, system: str, user: str, temperature: float = 0.4, model: str | None = None) -> str:
    if provider == 'openrouter':
        return call_openrouter(system, user, temperature=temperature, model=model)
    if provider == 'ollama':
        return call_ollama(system, user, temperature=temperature, model=model)
    raise ValueError('provider must be openrouter or ollama')

def load_prompt_sections(prompt_path: str) -> tuple[str,str]:
    with open(prompt_path,'r',encoding='utf-8') as f:
        template = f.read()
    lines = template.splitlines()
    system_start = user_start = None
    for i, ln in enumerate(lines):
        if ln.strip().lower().startswith('## system role'):
            system_start = i+1
        if ln.strip().lower().startswith('## user instructions'):
            user_start = i+1
            break
    if system_start is not None and user_start is not None:
        system_text = '\n'.join(lines[system_start:user_start-1]).strip()
        user_text = '\n'.join(lines[user_start:]).strip()
        return system_text, user_text
    return 'You are a helpful assistant. Return JSON only.', template

def parse_json_response(text: str) -> dict:
    cleaned = _strip_json(text)
    return json.loads(cleaned)
