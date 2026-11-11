import json
from pathlib import Path
import tempfile
import unittest
from nitro_sense.profiles import DEFAULT_PROFILE, ProfileStore, validate_profile


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)
    def test_save_import_export_roundtrip_without_hardware(self):
        store=ProfileStore(self.path);profile=validate_profile(DEFAULT_PROFILE);profile['name']='Gaming';profile['fan']={'cpu':60,'gpu':70}
        store.put(profile);store.export_file(profile,self.path/'export.json')
        reopened=ProfileStore(self.path);self.assertEqual(reopened.profiles[-1],profile)
        imported=reopened.import_file(self.path/'export.json');self.assertEqual(imported,profile)
        self.assertEqual(len(reopened.profiles),2)
    def test_invalid_values_rejected(self):
        for field,value in [('brightness',101),('colors',['red']*4),('type','shell'),('direction',-1)]:
            profile=json.loads(json.dumps(DEFAULT_PROFILE));profile['lighting'][field]=value
            with self.assertRaises(ValueError):validate_profile(profile)
        profile=json.loads(json.dumps(DEFAULT_PROFILE));profile['fan']['cpu']=True
        with self.assertRaises(ValueError):validate_profile(profile)
    def test_corrupt_database_keeps_defaults_and_reports_error(self):
        (self.path/'profiles.json').write_text('{invalid')
        store=ProfileStore(self.path);self.assertIsNotNone(store.error);self.assertEqual(store.profiles[0]['name'],'Default')
    def test_wrong_container_types_do_not_crash_startup(self):
        for value in ([], None, {'preferences': []}, {'preferences': None}):
            (self.path/'profiles.json').write_text(json.dumps(value))
            store=ProfileStore(self.path)
            self.assertIsNotNone(store.error)
            self.assertEqual(store.profiles[0]['name'],'Default')
    def test_unsupported_dynamic_effect_and_direction_rejected(self):
        for mode,direction in ((6,1),(7,1),(3,0),(4,0),(0,1)):
            profile=json.loads(json.dumps(DEFAULT_PROFILE))
            profile['lighting'].update(type='dynamic',mode=mode,direction=direction)
            with self.assertRaises(ValueError):validate_profile(profile)
    def test_large_import_rejected(self):
        path=self.path/'large.json';path.write_text(' '*65537)
        with self.assertRaises(ValueError):ProfileStore(self.path).import_file(path)


if __name__=='__main__':unittest.main()
