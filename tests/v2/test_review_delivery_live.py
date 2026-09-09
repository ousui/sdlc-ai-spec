"""Native-collector regressions: actual RLS and large input history, on macOS."""
import json
import random
import zipfile
from pathlib import Path
import unittest

import test_review_fixes as fixtures


class ReviewLiveDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.tearDown)
        self.c=self.f.c

    def close_delivery(self):
        c=self.c
        c.complete('VFY');step=c.task_start('rls')['data']['step_id']
        c.review('rls-condition')
        prepared=c.call('delivery.prepare',{'revision_id':c.rev,'lease_id':c.lease,'usage':'Run the preserved executable ./mvnw'})['data']
        sent=c.call('delivery.execute',{'delivery_id':prepared['delivery_id'],'lease_id':c.lease})['data']
        self.assertEqual('succeeded',sent['status'])
        c.call('task.finish',{'revision_id':c.rev,'task_id':c.ids['rls'],'step_id':step,'lease_id':c.lease,'summary':'Readback and required completion condition passed'})
        final=c.complete('RLS');self.assertTrue(final['ok'])
        return self.f.root/prepared['package_path']

    def test_rls_owned_condition_allows_real_vfy_then_verified_rls(self):
        self.f.implement()
        package=self.close_delivery()
        with zipfile.ZipFile(package) as z:
            self.assertEqual(0o100755,z.getinfo('code/main/mvnw').external_attr>>16)

    def test_more_than_64mib_inputs_remain_in_history_not_product_package(self):
        c=self.c;old_change=c.change
        c.call('change.revise',{'phase':'REQ','reason':'Keep large original inputs in the complete history archive'})
        p=c.call('phase.prepare',{'phase':'REQ'})['data'];c.rev=p['content']['revision']['revision_id'];c.gen=p['generation']
        inputs=self.f.root/'.sdlc/inputs';inputs.mkdir()
        for index in (1,2):
            path=inputs/f'history-{index}.bin';path.write_bytes(random.Random(index).randbytes(34*1024*1024))
            result=c.call('asset.add',{'path':path.relative_to(self.f.root).as_posix(),'owner_type':'source','owner_id':c.ids['source'],'purpose':'original history'},generation=True)['data']
            c.gen=result['generation']
        c.complete('REQ');c.complete('DSN');c.complete('PLN')
        self.f.implement()
        package=self.close_delivery()
        self.assertEqual(old_change,c.change)
        self.assertLess(package.stat().st_size,2*1024*1024)
        with zipfile.ZipFile(package) as z:
            index=json.loads(z.read('attachments.json'))
            self.assertEqual(68*1024*1024,sum(r['size_bytes'] for r in index['attachments']))
        archived=c.call('workspace.export',{'change_id':c.change},bind=False)['data']
        with zipfile.ZipFile(archived['path']) as z:
            rows=json.loads(z.read('database.json'))
            originals=[r for r in rows['assets'] if r['size_bytes']==34*1024*1024]
            self.assertEqual(2,len(originals))
            for row in originals:
                h=row['sha256'];self.assertEqual(34*1024*1024,len(z.read(f'assets/{h[:2]}/{h[2:4]}/{h}')))


if __name__=='__main__': unittest.main()
