#!/usr/bin/python3.2

verbose=True

standalone=True
ip='192.168.177.5'
ta_designer_xml=r"Neu.xml"
username = 'user'
password = 'gast123'
import logging
logging.basicConfig(level=logging.DEBUG)
    
    

#import pydevd
import re
import pprint
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.request import urlopen 


def fetch(url,username, password):
  import requests
  res=requests.get(url, auth=(username, password)).text
  print("########request")
  print(res)
  print(type(res))
  print("########request")  
  return res 



class MyHTMLParser(HTMLParser):
    def __init__(self,log):
      super().__init__()
      #HTMLParser.__init__(self)
      self.logging=log
      self.id = []
      self.data = []
      self.tag=None
      self.temp=[]
      self.dict={}
      self.curr_id=""
    def handle_starttag(self, tag, attrs):
      if tag != 'div':
        self.logging.debug('no div')
        return
      self.tag=tag
      self.temp=[]
      for attr in attrs:
            v=attr[1].split('pos')
            if len(v)>1:
                idx=v[1]
                self.id.append(int(idx))
                self.curr_id=int(idx)
                self.logging.debug('index '+str(idx) + " ")
    def handle_data(self, data):
      if self.tag=='div':
        self.logging.debug('div with data {} for id {}'.format(data, self.curr_id))
        self.temp.append(data)
      elif self.tag=='a':
        self.logging.debug('a with data {} for id {}'.format(data, self.curr_id))
        self.temp.append(data)
      else:
        self.logging.debug('Tag is neither a or div for id {}'.format(data, self.curr_id))      
    def handle_endtag(self, tag):
      if tag == 'div':
        s="".join(self.temp)
        self.logging.debug('Handle endtag {} for id {}'.format(s,self.curr_id))
        s=s.replace(',','.')
        s=s.replace('AUS','0')
        s=s.replace('EIN','1')
        s=s.replace('OFF','0')
        s=s.replace('ON','1')
        self.logging.debug('closing tag and saving{} for id {}'.format(s,self.curr_id))
        try:
            import re
            #s.encode()
            #self.logging.debug('Encoded {}'.format(s))
            #s.decode()
            self.logging.debug('Working on {}'.format(s))  
            non_decimal = re.compile(r'[^-\d.]+')
            w=non_decimal.sub('', s)
            if s.find('%')>0:
                w=float(w)/100
            self.logging.debug('Result is: {} for id {}'.format(w,self.curr_id))
        except Exception as e: 
            self.logging.warning('oh oh exception {} for value |{}|. String was|{}|'.format(e,w,s))

        self.data.append(w)
        self.dict[self.curr_id]=w



def read_xml(root, Seite):
    beschreibung=[]
    id_conf=[]
    xml_dict={}
    idx=0
    for i in range(0,len(root.findall('./Seiten/Seite_{}/Objekte/*'.format(Seite)))):
      b=  root.findall('./Seiten/Seite_{}/Objekte/Objekt_{}'.format(Seite,i))[-1].get('Bezeichnung').split(': ')[-1]
      typ=root.findall('./Seiten/Seite_{}/Objekte/Objekt_{}'.format(Seite,i))[-1].get('Objekt_Typ')
      #if not re.match('.*.(PNG|png)', b):
      if not "Pic_Obj" in typ:
          beschreibung.append(b)
          id_conf.append(idx)
          xml_dict[b]=idx
          #logging.debug('[UVR] XML_processing: Beschreibung {}, i {}, idx {}'.format(b, i, idx))
          idx+=1
      #else:
      #  logging.debug('[UVR] XML_processing: Not incrementing idx for Image {} for Bezeichnung {}'.format(typ,b))

#dict1=xml_dict 
#new_dict = {k:dict1[k] for k in dict1 if not re.match('.*.(PNG|png)', k)}
#xml_dict=new_dict

    logging.debug('[UVR] Available Strings in xml auf Seite {}:'.format(Seite))
    logging.debug(beschreibung)
    return beschreibung, id_conf, xml_dict


def read_html(ip,Seite,username,password,standalone):
    url='http://{}/schematic_files/{}.cgi'.format(ip,Seite+1)  # die Seiten/cgi starten mit 1; die xml-objekte mit 0
    logging.debug('Handling url {}'.format(url))    
    if True:
      if not standalone:
        h=sh.tools.fetch_url(url, username, password, timeout=60)  
      else: 
        h=fetch(url, username, password) 
      if h is not False: 
            html = h #str(h)
      else:
            html=h
    #except:
    #  html = None
    #  logging.error('[UVR] Could not fetch data for URL {}'.format(url))
    return(html)





def combine_html_xml(standalone, MyHTMLParser, beschreibung, id_conf, xml_dict, html):
    import pprint
    logging.debug("[UVR] HTML {0} End".format(html))

    parser = MyHTMLParser(logging)
    parser.feed(html)

    id_res=parser.id
    content=parser.data
    html_dict=parser.dict
    logging.debug("[UVR] HTML-dict {0}".format(pprint.pformat(html_dict)))
    logging.debug("[UVR] XML-dict {0}".format(pprint.pformat(xml_dict)))
        

        #-------------assign the results-------------------
        #we have four lists now:
        #config: id_conf, beschreibung
        #result: id_res, content
    logging.debug('[UVR] TA-XML id_conf {0}'.format(pprint.pformat(id_conf)))
    logging.debug('[UVR] TA-XML Beschreibung {0}'.format(pprint.pformat(beschreibung)))
    logging.debug('[UVR] HTML id_res {0}'.format(pprint.pformat(id_res)))
    logging.debug('[UVR] HTML content {0}'.format(pprint.pformat(content)))
    if len(content)!=len(id_conf):
       logging.error('[UVR] ERROR. Länge XML {} und HTML {} sind ungleich'.format(len(id_conf),len(content)))

    combined_dict={}
    for key, value in xml_dict.items():
        try:
          combined_dict[key]=html_dict[value]
        except Exception as err:
          logging.exception("[UVR] Error matching HTML and Item: {0}, {1}. Exception".format(key,value),exc_info=True)
                
        
    if standalone: 
       pprint.pprint(combined_dict)
    else:
       logging.debug("[UVR] Combined-dict {0}".format(pprint.pformat(combined_dict)))
    return combined_dict

def update_item(combined_dict, item):
    success=False
    UVRStr =""
    logging.debug("[UVR] Searching Suchstring {0} ".format(item))
    if 'UVRstring' in item.property.attributes:   
     try:
       UVRStr=item.conf['UVRstring']
       if UVRStr in combined_dict:
         val   =combined_dict[UVRStr]
         if val!=-99999 and val!='':
            item(val)
            success=True
            logging.info("[UVR] Suchstring {0} found. Value is {1}. Updating item".format(UVRStr,val))
         else:
            logging.debug("[UVR] Suchstring {0} found on this page. NOT Updating item (yet)".format(UVRStr))
       else:
         val   = None
     except KeyError:
       logging.error('[UVR] xmlstring is empty or not existent for item {0}'.format(item))
       pass
    return success, UVRStr



################# Main Loop #####################################

logging.info('[UVR] Starte Mainloop')

#read the configuration-----------------------------------------------------------------------------
tree   = ET.parse(ta_designer_xml)
root   = tree.getroot()
Seiten = range(0,len(root.findall('./Seiten/')))
combined_dict=[]

for Seite in Seiten:
    #----------read the page in xml-----------------------------
    beschreibung, id_conf, xml_dict=read_xml(root, Seite)
    #----------read the response-------------------------------
    html=read_html(ip,Seite,username,password,standalone)
    from datetime import datetime
    now = datetime.now()
    #with open("/usr/local/smarthome/var/log/"+now.strftime("%Y%m%d-%H%M%S")+"uvr.log", "w") as text_file:
    #   print(html, file=text_file)
    #----------combine xml and html----------------------------
    if (html is not None) and (html is not False):
        combined_dict.append( combine_html_xml(standalone, MyHTMLParser, beschreibung, id_conf, xml_dict, html) )          
    else: 
        logging.error('[UVR] html could not be loaded. html is {0}'.format(html))    


if not standalone:
    for item in UVRitems:
      item_updated=False
      for Seite in Seiten:
          success,UVRStr=update_item(combined_dict[Seite], item) 
          if success: item_updated=True

      if not item_updated and UVRStr!='': 
        logging.warning("[UVR] Suchstring {0} not found for item {1}".format(UVRStr,item))


    

