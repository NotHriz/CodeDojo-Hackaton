"""Verify disposable community projections with the existing public DTOs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from app.services.community import ClearanceResponse, CommunityCounts, ReportEventResponse, ReportResponse


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pg-bin',required=True)
    parser.add_argument('--port',required=True)
    args=parser.parse_args()
    command=[str(Path(args.pg_bin)/'psql.exe'),'-X','-h','127.0.0.1','-p',args.port,
             '-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1','-qAt']
    script="""BEGIN; SET LOCAL ROLE service_role;
INSERT INTO public.clearance_observations (id,report_id,report_observed_at,author_id,description,
    observed_at,idempotency_key,payload_digest)
SELECT '40000000-0000-0000-0000-000000000001',id,observed_at,
    '40000000-0000-0000-0000-000000000002','Fictional projected clearing claim',now(),
    '40000000-0000-0000-0000-000000000003',repeat('b',64)
FROM public.barrier_reports WHERE building_id='seed-test-building';
INSERT INTO public.report_events (report_id,action,new_status,supporters,disputes,actor_id)
SELECT id,'report_created','unverified',0,0,author_id FROM public.barrier_reports WHERE building_id='seed-test-building';
SELECT jsonb_build_object('reports',(SELECT jsonb_agg(record) FROM public.report_public_records),
    'history',(SELECT jsonb_agg(record ORDER BY occurred_at,sequence) FROM public.report_history_records));
ROLLBACK;"""
    result=subprocess.run(command,input=script,encoding='utf-8',capture_output=True,
                          env={**os.environ,'PGCLIENTENCODING':'UTF8'})
    assert result.returncode==0,result.stderr
    records=json.loads(result.stdout)
    assert len(records['reports'])==1 and len(records['history'])==1
    for raw in records['reports']:
        assert set(raw)==set(ReportResponse.model_fields),'Private/unexpected report fields'
        assert set(raw['community'])==set(CommunityCounts.model_fields)
        for child in raw['clearance_observations']:
            assert set(child)==set(ClearanceResponse.model_fields),'Private/unexpected clearing fields'
            assert set(child['community'])==set(CommunityCounts.model_fields)
        report=ReportResponse.model_validate(raw)
        assert report.place_id=='seed-test-building' and report.campus_id=='seed-test-campus'
        assert report.status=='unverified' and report.community.supporters==0
        assert len(report.clearance_observations)==1
        assert report.clearance_observations[0].evidence_urls==[]
        assert report.observed_at.tzinfo is not None and report.submitted_at.tzinfo is not None
        assert report.clearance_observations[0].observed_at>=report.observed_at
    for raw in records['history']:
        assert set(raw)==set(ReportEventResponse.model_fields),'Private/unexpected event fields'
        event=ReportEventResponse.model_validate(raw)
        assert event.report_id==report.id and event.previous_status is None
        assert event.action=='report_created' and event.community.supporters==0
    print('Community projection integration passed: PostgreSQL -> ReportResponse/ClearanceResponse/ReportEventResponse, privacy and timestamps.')


if __name__=='__main__':
    main()
