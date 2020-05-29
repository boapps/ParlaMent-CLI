import requests
import bs4
from datetime import datetime
from datetime import timedelta
import re

VOTE_URL = 'https://parlament.hu/web/guest/szavazasok-elozo-ciklusbeli-adatai?p_p_id=hu_parlament_cms_pair_portlet_PairProxy_INSTANCE_9xd2Wc9jP4z8&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&_hu_parlament_cms_pair_portlet_PairProxy_INSTANCE_9xd2Wc9jP4z8_pairAction=%2Finternet%2Fcplsql%2Fogy_szav.szav_irom%3FP_DATUM_TOL%3D{start}%26P_CKL%3D{cycle}%26P_DATUM_IG%3D{end}'
CYCLES_URL = 'https://www.parlament.hu/web/guest/szavazasok-elozo-ciklusbeli-adatai'
DAYS_URL = 'https://www.parlament.hu/naplo{cycle}/index.htm'


class Vote:
    def __init__(self, date, mode, yes_count, no_count, neutral_count, count, acceptance, note, attachments):
        self.date = date
        self.mode = mode
        self.yes_count = yes_count
        self.no_count = no_count
        self.neutral_count = neutral_count
        self.count = count
        self.acceptance = acceptance
        self.note = note
        self.attachments = attachments

    def __str__(self):
        return '''{0}:
    mode: {1}
    yes: {2}
    no: {3}
    neutral: {4}
    total: {5}
    acceptance: {6}
    note: {7}
    attachments:
    {8}'''.format(
            self.date, self.mode, self.yes_count, self.no_count, self.neutral_count, self.count,
            self.acceptance, self.note, ','.join([str(att) for att in self.attachments])
        )

    def __repr__(self):
        return str(self)


class VoteAttachment:
    def __init__(self, writing, separate_voting, title, authors, reason, politician):
        self.writing = writing
        self.seperate_voting = separate_voting
        self.title = title
        self.authors = authors
        self.reason = reason
        self.politician = politician

    def __str__(self):
        return '''{{
        {2}:
        writing: {0}
        separate_voting: {1}
        authors: {3}
        reason: {4}
        politician: {5}
    }}'''.format(self.writing, self.seperate_voting, self.title, self.authors, self.reason, self.politician)

    def __repr__(self):
        return str(self)


class PrimeMinister:
    def __init__(self, name, start, end):
        self.name = name
        self.start = start
        self.end = end

    def __str__(self):
        return '{0} ({1}-{2})'.format(self.name, self.start, self.end)

    def __repr__(self):
        return str(self)


class Cycle:
    def __init__(self, cycle_id, name, start, end, prime_ministers):
        self.cycle_id = cycle_id
        self.name = name
        self.start = start
        self.end = end
        self.prime_ministers = prime_ministers

    def __str__(self):
        return '''{0}.:
    {1}
    {2} - {3}
        {4} 
        '''.format(str(self.cycle_id), self.name, self.start, self.end, '\n\t'.join(
            [str(pm) for pm in self.prime_ministers]
        ))

    def __repr__(self):
        return str(self)


def get_cycles():
    cycles = list()
    response = requests.get(CYCLES_URL)
    soup = bs4.BeautifulSoup(response.content, 'html.parser')
    table = soup.find_all('tbody')[0]
    for row in table.children:
        if type(row) == bs4.element.Tag:
            cycle_id = int(list(row.children)[1].text)
            cycle_name = list(row.children)[3].text.strip()
            cycle_start = list(row.children)[5].text.strip()
            cycle_end = list(row.children)[7].text.strip()
            prime_minister_list = list()

            prime_minister_name_list = list()
            prime_minister_start_list = list()
            prime_minister_end_list = list()
            for prime_minister_name in list(row.children)[9].children:
                if type(prime_minister_name) == bs4.element.Tag:
                    name = prime_minister_name.text.strip()
                    if len(name) > 0:
                        prime_minister_name_list.append(name)

            for prime_minister_start in list(row.children)[11].children:
                if '<br/>' not in str(prime_minister_start):
                    prime_minister_start_list.append(str(prime_minister_start).strip())

            for prime_minister_end in list(row.children)[13].children:
                if '<br/>' not in str(prime_minister_end):
                    prime_minister_end_list.append(str(prime_minister_end).strip())

            for name, start, end in zip(prime_minister_name_list, prime_minister_start_list, prime_minister_end_list):
                prime_minister_list.append(PrimeMinister(name, start, end))

            cycles.append(Cycle(cycle_id, cycle_name, cycle_start, cycle_end, prime_minister_list))
    return cycles


def get_days(cycle):
    response = requests.get(DAYS_URL.format(cycle=cycle))
    days_content = str(response.content)

    if int(cycle) >= 40:
        days = re.findall('p_nap=([0-9]+)', days_content)
        day_names = re.findall('p_nap=[0-9]*">([0-9\.]*)', days_content)
    elif int(cycle) >= 38:
        days = re.findall('href="/naplo'+cycle+'/([0-9]*)/[0-9]*\.htm', days_content)
        day_names = re.findall('<td>([0-9\.]+)', days_content)
    elif int(cycle) >= 36:
        days = re.findall('href="([0-9]*)/[0-9]*\.htm', days_content)
        day_names = re.findall('<td>\ ([0-9\.]+)', days_content)
    elif int(cycle) == 35:
        days = re.findall('href="../naplo'+cycle+'/([0-9]*)/[0-9]*tart\.htm', days_content)
        day_names = re.findall('[0-9]{4}\.[0-9]{2}\.[0-9]{2}', days_content)
    else:
        days = re.findall('href="/naplo'+cycle+'/([0-9]*)/[0-9]*tart\.htm', days_content)
        day_names = re.findall('[0-9]{4}\.[0-9]{2}\.[0-9]{2}', days_content)

    return list(zip(days, day_names))


def get_votes(selected_cycle, start, end):
    votes = list()
    response = requests.get(VOTE_URL.format(cycle=selected_cycle, start=start, end=end))
    soup = bs4.BeautifulSoup(response.content, 'html.parser')
    for vote_div in soup.find_all('div', {'class': 'egy-szavazas'}):
        vote_date = vote_div.find('div', {'class': 'szav-idopont'}).table.tbody.tr.td.a.text.strip()

        vote_table = vote_div.find('div', {'class': 'szav-adatok'}).div.div.table.tbody
        vote_table_keys = vote_table.find_all('td', {'class': ''}, recursive=True)
        vote_table_values = vote_table.find_all('td', {'class': 'lefted'}, recursive=True)
        vote_table_dict = dict(zip(
            [element.text.strip() for element in vote_table_keys],
            [element.text.strip() for element in vote_table_values]
        ))

        vote_mode = vote_table_dict['Szavazási mód']
        if '"Igen"-ek száma' in vote_table_dict:
            vote_yes_count = int(vote_table_dict['"Igen"-ek száma'])
        else:
            vote_yes_count = -1
        if '"Nem"-ek száma' in vote_table_dict:
            vote_no_count = int(vote_table_dict['"Nem"-ek száma'])
        else:
            vote_no_count = -1
        if 'Tartózkodások' in vote_table_dict:
            vote_neutral_count = int(vote_table_dict['Tartózkodások'])
        else:
            vote_neutral_count = -1
        if 'Összes szavazat' in vote_table_dict:
            vote_count = int(vote_table_dict['Összes szavazat'])
        else:
            vote_count = -1
        if 'Elfogadás' in vote_table_dict:
            vote_acceptance = vote_table_dict['Elfogadás']
        else:
            vote_acceptance = ''
        if 'Megjegyzés' in vote_table_dict:
            vote_note = vote_table_dict['Megjegyzés']
        else:
            vote_note = ''

        vote_attachments_table = vote_div.find('div', {'class': 'szav-inditvanyok'}).div.div.table
        vote_attachments_values = vote_attachments_table.find_all('td')
        vote_attachments_keys = vote_attachments_table.find_all('th')[1:]
        vote_attachments_dict = dict(zip(
            [element.text.strip() for element in vote_attachments_keys],
            [element.text.strip() for element in vote_attachments_values]
        ))

        vote_attachments = list()
        if 'Iromány' in vote_attachments_dict:
            vote_attachment_paper = vote_attachments_dict['Iromány']
        else:
            vote_attachment_paper = ''
        if 'Külön szavazásra kért pont' in vote_attachments_dict:
            vote_attachment_separate_voting = vote_attachments_dict['Külön szavazásra kért pont']
        else:
            vote_attachment_separate_voting = ''
        if 'Cím' in vote_attachments_dict:
            vote_attachment_title = vote_attachments_dict['Cím']
        else:
            vote_attachment_title = ''
        if 'Benyújtók' in vote_attachments_dict:
            vote_attachment_authors = vote_attachments_dict['Benyújtók']
        else:
            vote_attachment_authors = ''
        if 'Szavazás oka' in vote_attachments_dict:
            vote_attachment_reason = vote_attachments_dict['Szavazás oka']
        else:
            vote_attachment_reason = ''
        if 'Képviselő' in vote_attachments_dict:
            vote_attachment_politician = vote_attachments_dict['Képviselő']
        else:
            vote_attachment_politician = ''
        vote_attachment = VoteAttachment(
            vote_attachment_paper, vote_attachment_separate_voting, vote_attachment_title,
            vote_attachment_authors, vote_attachment_reason, vote_attachment_politician
        )
        vote_attachments.append(vote_attachment)

        vote = Vote(
            vote_date, vote_mode, vote_yes_count, vote_no_count, vote_neutral_count,
            vote_count, vote_acceptance, vote_note, vote_attachments
        )
        votes.append(vote)
    return votes


def real_children(element):
    return list(filter(lambda child: type(child) == bs4.element.Tag, element.children))


def get_which_cycle(cycles, date):
    for cycle in cycles:
        if datetime.strptime(cycle.start, '%Y.%m.%d.') < date:
            return cycle


def main():
    print(
        '{0:6} {1:>12} {2:>12} {3:>12} {4:>22} {5:>12} {6:>12}'.format(
        'ciklus', 'név', 'kezdet', 'vége', 'miniszterelnök', 'kezdet', 'vége'
        ))

    cycles = get_cycles()

    for cycle in cycles:
        print(
            '{0:6} {1:>12} {2:>12} {3:>12} {4:>22} {5:>12} {6:>12}'.format(
            cycle.cycle_id, cycle.name, cycle.start, cycle.end, cycle.prime_ministers[0].name,
                cycle.prime_ministers[0].start, cycle.prime_ministers[0].end
            ))
        if len(cycle.prime_ministers) > 1:
            for pm in cycle.prime_ministers[1:]:
                print('{0:>68} {1:>12} {2:>12}'.format(pm.name, pm.start, pm.end))

    print('Szavazások mutatása adott ciklusban, két időpont között')

    today_date = datetime.now()
    week_ago_date = today_date - timedelta(days=7)
    selected_start_str = week_ago_date.strftime("%Y.%m.%d")
    selected_end_str = today_date.strftime("%Y.%m.%d")

    selected_start = input('kezdet [{}]: '.format(selected_start_str)).strip()
    if selected_start == '':
        selected_start = selected_start_str

    selected_cycle = get_which_cycle(cycles, datetime.strptime(selected_start, '%Y.%m.%d'))

    selected_end = input('vége [{}]: '.format(selected_end_str)).strip()
    if selected_end == '':
        selected_end = selected_end_str

    votes = get_votes(selected_cycle.cycle_id, selected_start, selected_end)
    for vote in votes:
        print(vote)


if __name__ == "__main__":
    main()
