import requests
import bs4
import re
import parlament_vote
import shutil

DAY_URL = 'https://www.parlament.hu/web/guest/videoarchivum?p_p_id=hu_parlament_cms_pair_portlet_PairProxy_INSTANCE_9xd2Wc9jP4z8&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_auth=qJ6t6jPq&_hu_parlament_cms_pair_portlet_PairProxy_INSTANCE_9xd2Wc9jP4z8_pairAction=%2Finternet%2Fcplsql%2Fogy_naplo.ulnap_felszo%3Fp_lista%3DA%26p_nap%3D{day}%26p_ckl%3D{cycle}'


def download_m3u8(m3u8_url, selected_duration, start_sec):
    base_url = m3u8_url.replace(m3u8_url.split('/')[-1], '')
    m3u8_response = requests.get(m3u8_url)
    m3u8_content = str(m3u8_response.content)
    chunks = [base_url + chunk for chunk in re.findall('media[\w]*.ts', m3u8_content)]
    durations = re.findall('#EXTINF:([0-9\.]*)', m3u8_content)
    downloaded_duration = 0
    with open('test.mp4', 'wb') as out_file:
        for chunk_url, duration in zip(chunks, durations):
            response = requests.get(chunk_url, stream=True)
            shutil.copyfileobj(response.raw, out_file)
            downloaded_duration += float(duration)

            if downloaded_duration >= selected_duration:
                break


def get_resolutions(m3u8_url):
    m3u8_response = requests.get(m3u8_url)
    m3u8_content = str(m3u8_response.content)
    resolutions = re.findall('RESOLUTION=([0-9x]*)', m3u8_content)
    chunklists = [m3u8_url.replace('playlist.m3u8', chunklist) for chunklist in re.findall('chunklist[\w]*.m3u8', m3u8_content)]
    return dict(zip(resolutions, chunklists))


def get_m3u8_url(cycle, day):
    return get_f4m_url(cycle, day).replace('manifest.f4m', 'playlist.m3u8')


def get_f4m_url(cycle, day):
    day_response = requests.get(DAY_URL.format(cycle=cycle, day=day))
    day_soup = bs4.BeautifulSoup(day_response.content, 'html.parser')
    flash_url = day_soup.find('a', {'class': 'not-load-video'})['href']
    flash_response = requests.get(flash_url, verify=False)
    body = str(flash_response.content)
    start = body.index('playSmil(\\\'') + len('playSmil(\\\'')
    end = body.index("'", start) - 1
    f4m_url = body[start:end].replace('playlist.m3u8', 'manifest.f4m')
    return f4m_url


def getDuration(f4m_url):
    f4m_response = requests.get(f4m_url)
    return re.findall(r'<duration>(.*)</duration>', str(f4m_response.content))[0]


def getResolutions(f4m_url):
    f4m_response = requests.get(f4m_url)
    return re.findall(r'height="(\w*)"', str(f4m_response.content))


print(
    '{0:6} {1:>12} {2:>12} {3:>12} {4:>22} {5:>12} {6:>12}'.format(
    'ciklus', 'név', 'kezdet', 'vége', 'miniszterelnök', 'kezdet', 'vége'
    ))

cycles = parlament_vote.get_cycles()

for cycle in cycles:
    print(
        '{0:6} {1:>12} {2:>12} {3:>12} {4:>22} {5:>12} {6:>12}'.format(
        cycle.cycle_id, cycle.name, cycle.start, cycle.end, cycle.prime_ministers[0].name,
            cycle.prime_ministers[0].start, cycle.prime_ministers[0].end
        ))
    if len(cycle.prime_ministers) > 1:
        for pm in cycle.prime_ministers[1:]:
            print('{0:>68} {1:>12} {2:>12}'.format(pm.name, pm.start, pm.end))

selected_cycle = input('válassz ciklust: ')
if int(selected_cycle) not in [cycle.cycle_id for cycle in cycles]:
    print('nincs ilyen ciklus')

days = parlament_vote.get_days(selected_cycle)
print('dátum      ', 'nap')
for day, day_name in days:
    print(day_name, day)
selected_day = input('válassz ülésnapot [{}]: '.format(days[0][0])).strip()
if selected_day == '':
    selected_day = days[0][0]
f4m_url = get_f4m_url(selected_cycle, selected_day)
m3u8_url = get_m3u8_url(selected_cycle, selected_day)
res_dict = get_resolutions(m3u8_url)
print('lehetséges felbontások:', ', '.join(res_dict.keys()))
selected_resolution = input('felbontás [{}]: '.format(list(res_dict.keys())[-1]))
if selected_resolution == '':
    selected_resolution = list(res_dict.keys())[-1]
duration = getDuration(f4m_url)
selected_duration = float(input('hossz [{}]: '.format(duration)))

download_m3u8(res_dict[selected_resolution], selected_duration, 0)
