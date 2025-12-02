import threading
import time
from app.scrapers.now.elevon.drhorton import DRHortonElevonNowScraper
from app.scrapers.now.elevon.unionmain import UnionMainElevonNowScraper
from app.scrapers.now.elevon.historymaker import HistoryMakerElevonNowScraper
from app.scrapers.now.elevon.mihomes import MIHomesElevonNowScraper
from app.scrapers.now.elevon.trophysignature import TrophySignatureElevonNowScraper
from app.scrapers.now.elevon.pacesetter import PacesetterElevonNowScraper
from app.scrapers.now.elevon.khovnanian import KHovnanianElevonNowScraper
from app.scrapers.plans.elevon.drhorton import DRHortonElevonPlanScraper
from app.scrapers.plans.elevon.unionmain import UnionMainElevonPlanScraper
from app.scrapers.plans.elevon.historymaker import HistoryMakerElevonPlanScraper
from app.scrapers.plans.elevon.khovnanian import KHovnanianElevonPlanScraper
from app.scrapers.plans.elevon.mihomes import MIHomesElevonPlanScraper
from app.scrapers.plans.elevon.pacesetter import PacesetterElevonPlanScraper
from app.scrapers.plans.elevon.trophysignature import TrophySignatureElevonPlanScraper
from app.scrapers.now.cambridge.unionmain import UnionMainCambridgeNowScraper
from app.scrapers.now.cambridge.coventry import CoventryCambridgeNowScraper
from app.scrapers.now.cambridge.highlandhomes import HighlandHomesCambridgeNowScraper
from app.scrapers.now.cambridge.amlegendhomes import AmericanLegendHomesCambridgeNowScraper
from app.scrapers.now.cambridge.trophysignature import TrophySignatureCambridgeNowScraper
from app.scrapers.plans.cambridge.trophysignature import TrophySignatureCambridgePlanScraper
from app.scrapers.now.cambridge.brightlandhomes import BrightlandHomesCambridgeNowScraper
from app.scrapers.now.milrany.unionmain import UnionMainMilranyNowScraper
from app.scrapers.now.milrany.bloomfield import BloomfieldMilranyNowScraper
from app.scrapers.now.milrany.pacesetter import PacesetterMilranyNowScraper
from app.scrapers.plans.milrany.unionmain import UnionMainMilranyPlanScraper
from app.scrapers.plans.milrany.pacesetter import PacesetterMilranyPlanScraper
from app.scrapers.plans.cambridge.unionmain import UnionMainCambridgePlanScraper
from app.scrapers.plans.cambridge.coventry import CoventryCambridgePlanScraper
from app.scrapers.plans.cambridge.highlandhomes import HighlandHomesCambridgePlanScraper
from app.scrapers.plans.cambridge.amlegendhomes import AmericanLegendHomesCambridgePlanScraper
from app.scrapers.plans.cambridge.brightlandhomes import BrightlandHomesCambridgePlanScraper
from app.scrapers.now.brookville.beazerhomes import BeazerHomesBrookvilleNowScraper
from app.scrapers.now.brookville.trophysignature import TrophySignatureBrookvilleNowScraper
from app.scrapers.now.brookville.highlandhomes import HighlandHomesBrookvilleNowScraper
from app.scrapers.now.brookville.unionmain import UnionMainBrookvilleNowScraper
from app.scrapers.now.brookville.perryhomes import PerryHomesBrookvilleNowScraper
from app.scrapers.now.brookville.historymaker import HistoryMakerBrookvilleNowScraper
from app.scrapers.now.brookville.ashtonwoods import AshtonWoodsBrookvilleNowScraper
from app.scrapers.now.brookville.shaddockhomes import ShaddockHomesBrookvilleNowScraper
from app.scrapers.now.edgewater.unionmain import UnionMainEdgewaterNowScraper
from app.scrapers.now.edgewater.perryhomes import PerryHomesEdgewaterNowScraper
from app.scrapers.now.edgewater.coventryhomes import CoventryHomesEdgewaterNowScraper
from app.scrapers.now.edgewater.chesmarhomes import ChesmarHomesEdgewaterNowScraper
from app.scrapers.plans.edgewater.unionmain import UnionMainEdgewaterPlanScraper
from app.scrapers.plans.edgewater.coventryhomes import CoventryHomesEdgewaterPlanScraper
from app.scrapers.now.creekside.unionmainhomes import UnionMainCreeksideNowScraper
from app.scrapers.now.creekside.highlandhomes import HighlandHomesCreeksideNowScraper
from app.scrapers.now.creekside.davidweekleyhomes import DavidWeekleyHomesCreeksideNowScraper
from app.scrapers.now.creekside.williamryanhomes import WilliamRyanHomesCreeksideNowScraper
from app.scrapers.now.creekside.rockwellhomes import RockwellHomesCreeksideNowScraper
from app.scrapers.now.maddox.unionmain import UnionMainMaddoxNowScraper
from app.scrapers.now.maddox.drhorton import DRHortonMaddoxNowScraper
from app.scrapers.now.maddox.chafincommunities import ChafinCommunitiesMaddoxNowScraper
from app.scrapers.now.maddox.davidhomes import DavidHomesMaddoxNowScraper
from app.scrapers.now.maddox.eastwoodhomes import EastwoodHomesMaddoxNowScraper
from app.scrapers.now.maddox.fischerhomes import FischerHomesMaddoxNowScraper
from app.scrapers.plans.brookville.beazerhomes import BeazerHomesBrookvillePlanScraper
from app.scrapers.plans.creekside.unionmainhomes import UnionMainHomesCreeksidePlanScraper
from app.scrapers.plans.creekside.highlandhomes import HighlandHomesCreeksidePlanScraper
from app.scrapers.plans.creekside.davidweekleyhomes import DavidWeekleyHomesCreeksidePlanScraper
from app.scrapers.plans.creekside.williamryanhomes import WilliamRyanHomesCreeksidePlanScraper
from app.scrapers.plans.creekside.rockwellhomes import RockwellHomesCreeksidePlanScraper
from app.scrapers.plans.brookville.highlandhomes import HighlandHomesBrookvillePlanScraper
from app.scrapers.plans.brookville.unionmain import UnionMainBrookvillePlanScraper
from app.scrapers.plans.brookville.perryhomes import PerryHomesBrookvillePlanScraper
from app.scrapers.plans.brookville.historymaker import HistoryMakerBrookvillePlanScraper
from app.scrapers.plans.brookville.ashtonwoods import AshtonWoodsBrookvillePlanScraper
from app.scrapers.plans.brookville.shaddockhomes import ShaddockHomesBrookvillePlanScraper
from app.scrapers.plans.maddox.unionmain import UnionMainMaddoxPlanScraper
from app.scrapers.plans.maddox.drhorton import DRHortonMaddoxPlanScraper
from app.scrapers.plans.maddox.chafincommunities import ChafinCommunitiesMaddoxPlanScraper
from app.scrapers.plans.maddox.davidhomes import DavidHomesMaddoxPlanScraper
from app.scrapers.plans.maddox.eastwoodhomes import EastwoodHomesMaddoxPlanScraper
from app.scrapers.plans.maddox.fischerhomes import FischerHomesMaddoxPlanScraper
from app.scrapers.now.echopark.unionmain import UnionMainEchoParkNowScraper
from app.scrapers.now.echopark.millcroft import MillcroftEchoParkNowScraper
from app.scrapers.now.echopark.evanshire import EvanshireEchoParkNowScraper
from app.scrapers.now.echopark.wardscrossing import WardsCrossingEchoParkNowScraper
from app.scrapers.now.echopark.watersidecondos import WatersideCondosEchoParkNowScraper
from app.scrapers.now.echopark.watersidetownhomes import WatersideTownhomesEchoParkNowScraper
from app.scrapers.now.echopark.kittlehomes import KittleHomesEchoParkNowScraper
from app.scrapers.plans.echopark.millcroft import MillcroftEchoParkPlanScraper
from app.scrapers.plans.echopark.evanshire import EvanshireEchoParkPlanScraper
from app.scrapers.plans.echopark.wardscrossing import WardsCrossingEchoParkPlanScraper
from app.scrapers.plans.echopark.watersidecondos import WatersideCondosEchoParkPlanScraper
from app.scrapers.plans.echopark.watersidetownhomes import WatersideTownhomesEchoParkPlanScraper
from app.scrapers.now.lakebreeze.unionmain import UnionMainLakeBreezeNowScraper
from app.scrapers.now.lakebreeze.bluehavenhomes import BlueHavenHomesLakeBreezeNowScraper
from app.scrapers.now.lakebreeze.christiehomes import ChristieHomesLakeBreezeNowScraper
from app.scrapers.now.lakebreeze.trophysignaturehomes import TrophySignatureHomesLakeBreezeNowScraper
from app.scrapers.now.lakebreeze.bloomfieldhomes import BloomFieldHomesLakeBreezeNowScraper
from app.scrapers.now.myrtlecreek.unionmain import UnionMainMyrtleCreekNowScraper
from app.scrapers.now.myrtlecreek.bloomfieldhomes import BloomFieldHomesMyrtleCreekNowScraper
from app.scrapers.now.myrtlecreek.highlandhomes import HighlandHomesMyrtleCreekNowScraper
from app.scrapers.now.myrtlecreek.chesmarhomes import ChesmarHomesMyrtleCreekNowScraper
from app.scrapers.now.myrtlecreek.davidweekleyhomes import DavidWeekleyHomesMyrtleCreekNowScraper
from app.scrapers.now.reunion.unionmainhomes import UnionMainHomesReunionNowScraper
from app.scrapers.now.reunion.beazerhomes import BeazerHomesReunionNowScraper
from app.scrapers.now.reunion.drhorton_bluestem import DRHortonBluestemNowScraper
from app.scrapers.plans.lakebreeze.unionmain import UnionMainLakeBreezePlanScraper
from app.scrapers.plans.lakebreeze.bluehavenhomes import BlueHavenHomesLakeBreezePlanScraper
from app.scrapers.plans.myrtlecreek.unionmain import UnionMainMyrtleCreekPlanScraper
from app.scrapers.plans.myrtlecreek.highlandhomes import HighlandHomesMyrtleCreekPlanScraper
from app.scrapers.plans.myrtlecreek.chesmarhomes import ChesmarHomesMyrtleCreekPlanScraper
from app.scrapers.plans.myrtlecreek.davidweekleyhomes import DavidWeekleyHomesMyrtleCreekPlanScraper
from app.scrapers.plans.reunion.unionmainhomes import UnionMainHomesReunionPlanScraper
from app.scrapers.plans.reunion.drhorton import DRHortonReunionPlanScraper
from app.scrapers.plans.reunion.beazerhomes import BeazerHomesReunionPlanScraper
from app.scrapers.plans.reunion.drhorton_bluestem import DRHortonBluestemPlanScraper
from app.scrapers.now.pickensbluff.unionmain import UnionMainPickensBluffNowScraper
from app.scrapers.now.pickensbluff.drhorton import DRHortonPickensBluffNowScraper
from app.scrapers.now.pickensbluff.starlighthomes import StarlightHomesPickensBluffNowScraper
from app.scrapers.now.pickensbluff.piedmontresidential import PiedmontResidentialPickensBluffNowScraper
from app.scrapers.plans.pickensbluff.unionmain import UnionMainPickensBluffPlanScraper
from app.scrapers.plans.pickensbluff.drhorton import DRHortonPickensBluffPlanScraper
from app.scrapers.plans.pickensbluff.starlighthomes import StarlightHomesPickensBluffPlanScraper
from app.scrapers.plans.pickensbluff.piedmontresidential import PiedmontResidentialPickensBluffPlanScraper
from app.scrapers.plans.wildflowerranch.unionmain import UnionMainWildflowerRanchPlanScraper
from app.scrapers.plans.wildflowerranch.amlegendhomes import AmericanLegendHomesWildflowerRanchPlanScraper
from app.scrapers.plans.wildflowerranch.drhorton import DRHortonWildflowerRanchPlanScraper
from app.scrapers.plans.wildflowerranch.davidweekleyhomes import DavidWeekleyHomesWildflowerRanchPlanScraper
from app.scrapers.plans.wildflowerranch.pulte import PulteWildflowerRanchPlanScraper
from app.scrapers.plans.wildflowerranch.mihorton import MIHortonWildflowerRanchPlanScraper
from app.scrapers.now.wildflowerranch.amlegendhomes import AmericanLegendHomesWildflowerRanchNowScraper
from app.scrapers.now.wildflowerranch.drhorton import DRHortonWildflowerRanchNowScraper
from app.scrapers.now.wildflowerranch.davidweekleyhomes import DavidWeekleyHomesWildflowerRanchNowScraper
from app.scrapers.now.wildflowerranch.pulte import PulteWildflowerRanchNowScraper
from app.scrapers.now.wildflowerranch.kbhome import KBHomeWildflowerRanchNowScraper
from app.scrapers.now.wildflowerranch.mihorton import MIHortonWildflowerRanchNowScraper
from app.scrapers.now.pickensbluff.davidsonhomes import DavidsonHomesPickensBluffNowScraper
from app.scrapers.plans.pickensbluff.fischerhomes import FischerHomesPickensBluffPlanScraper
from app.scrapers.now.pickensbluff.fischerhomes import FischerHomesPickensBluffNowScraper
from app.scrapers.plans.pickensbluff.fischerhomes_laurel_farms import FischerHomesLaurelFarmsPlanScraper
from app.scrapers.now.pickensbluff.fischerhomes_laurel_farms import FischerHomesLaurelFarmsNowScraper
from app.scrapers.plans.pickensbluff.fischerhomes_sage_woods import FischerHomesSageWoodsPlanScraper
from app.scrapers.now.pickensbluff.fischerhomes_sage_woods import FischerHomesSageWoodsNowScraper
from app.scrapers.plans.waldenpondwest.brightland import BrightlandWaldenPondWestPlanScraper
from app.scrapers.plans.waldenpondwest.unionmain import UnionMainWaldenPondWestPlanScraper
from app.scrapers.plans.waldenpondwest.pacesetter import PacesetterWaldenPondWestPlanScraper
from app.scrapers.plans.waldenpondwest.centex import CentexWaldenPondWestPlanScraper
from app.scrapers.plans.waldenpondwest.historymaker import HistoryMakerWaldenPondWestPlanScraper
from app.scrapers.now.waldenpondwest.brightland import BrightlandWaldenPondWestNowScraper
from app.scrapers.now.waldenpondwest.unionmain import UnionMainWaldenPondWestNowScraper
from app.scrapers.now.waldenpondwest.pacesetter import PacesetterWaldenPondWestNowScraper
from app.scrapers.now.waldenpondwest.centex import CentexWaldenPondWestNowScraper
from app.scrapers.now.waldenpondwest.historymaker import HistoryMakerWaldenPondWestNowScraper
from app.db.session import SessionLocal
from app.services.change_detection import detect_and_update_changes

SCRAPE_INTERVAL_SECONDS = 3600  # 5 minutes

class ScraperScheduler:
    def __init__(self):
        # Add all scraper instances here as you implement more
        self.scrapers = [
            # DRHortonElevonNowScraper(),
            # UnionMainElevonNowScraper(),
            # HistoryMakerElevonNowScraper(),
            # MIHomesElevonNowScraper(),
            # TrophySignatureElevonNowScraper(),
            # PacesetterElevonNowScraper(),
            # KHovnanianElevonNowScraper(),
            # DRHortonElevonPlanScraper(),
            # UnionMainElevonPlanScraper(),
            # HistoryMakerElevonPlanScraper(),
            # KHovnanianElevonPlanScraper(),
            # MIHomesElevonPlanScraper(),
            # PacesetterElevonPlanScraper(),
            # TrophySignatureElevonPlanScraper(),
            # UnionMainCambridgeNowScraper(),
            # CoventryCambridgeNowScraper(),
            # HighlandHomesCambridgeNowScraper(),
            # AmericanLegendHomesCambridgeNowScraper(),
            # TrophySignatureCambridgeNowScraper(),
            # TrophySignatureCambridgePlanScraper(),
            # BrightlandHomesCambridgeNowScraper(),
            # UnionMainMilranyNowScraper(),
            # BloomfieldMilranyNowScraper(),
            # PacesetterMilranyNowScraper(),
            # UnionMainMilranyPlanScraper(),
            # PacesetterMilranyPlanScraper(),
            # UnionMainCambridgePlanScraper(),
            # CoventryCambridgePlanScraper(),
            # HighlandHomesCambridgePlanScraper(),
            # AmericanLegendHomesCambridgePlanScraper(),
            # BrightlandHomesCambridgePlanScraper(),
            # BeazerHomesBrookvilleNowScraper(),
            # TrophySignatureBrookvilleNowScraper(),
            # HighlandHomesBrookvilleNowScraper(),
            # UnionMainBrookvilleNowScraper(),
            # PerryHomesBrookvilleNowScraper(),
            # HistoryMakerBrookvilleNowScraper(),
            # AshtonWoodsBrookvilleNowScraper(),
            # ShaddockHomesBrookvilleNowScraper(),
            UnionMainEdgewaterNowScraper(),
            # PerryHomesEdgewaterNowScraper(),
            # CoventryHomesEdgewaterNowScraper(),
            # ChesmarHomesEdgewaterNowScraper(),
            UnionMainEdgewaterPlanScraper(),
            # CoventryHomesEdgewaterPlanScraper(),
            # UnionMainCreeksideNowScraper(),
            # HighlandHomesCreeksideNowScraper(),
            # DavidWeekleyHomesCreeksideNowScraper(),
            # WilliamRyanHomesCreeksideNowScraper(),
            # RockwellHomesCreeksideNowScraper(),
            # UnionMainMaddoxNowScraper(),
            # DRHortonMaddoxNowScraper(),
            # ChafinCommunitiesMaddoxNowScraper(),
            # DavidHomesMaddoxNowScraper(),
            # EastwoodHomesMaddoxNowScraper(),
            # FischerHomesMaddoxNowScraper(),
            # BeazerHomesBrookvillePlanScraper(),
            # UnionMainHomesCreeksidePlanScraper(),
            # HighlandHomesCreeksidePlanScraper(),
            # DavidWeekleyHomesCreeksidePlanScraper(),
            # WilliamRyanHomesCreeksidePlanScraper(),
            # RockwellHomesCreeksidePlanScraper(),
            # HighlandHomesBrookvillePlanScraper(),
            # UnionMainBrookvillePlanScraper(),
            # PerryHomesBrookvillePlanScraper(),
            # HistoryMakerBrookvillePlanScraper(),
            # AshtonWoodsBrookvillePlanScraper(),
            # ShaddockHomesBrookvillePlanScraper(),
            # UnionMainMaddoxPlanScraper(),
            # DRHortonMaddoxPlanScraper(),
            # ChafinCommunitiesMaddoxPlanScraper(),
            # DavidHomesMaddoxPlanScraper(),
            # EastwoodHomesMaddoxPlanScraper(),
            # FischerHomesMaddoxPlanScraper(),
            # UnionMainEchoParkNowScraper(),
            # MillcroftEchoParkNowScraper(),
            # EvanshireEchoParkNowScraper(),
            # WardsCrossingEchoParkNowScraper(),
            # WatersideCondosEchoParkNowScraper(),
            # WatersideTownhomesEchoParkNowScraper(),
            # KittleHomesEchoParkNowScraper(),
            # MillcroftEchoParkPlanScraper(),
            # EvanshireEchoParkPlanScraper(),
            # WardsCrossingEchoParkPlanScraper(),
            # WatersideCondosEchoParkPlanScraper(),
            # WatersideTownhomesEchoParkPlanScraper(),
            # UnionMainLakeBreezeNowScraper(),
            # BlueHavenHomesLakeBreezeNowScraper(),
            # ChristieHomesLakeBreezeNowScraper(),
            # TrophySignatureHomesLakeBreezeNowScraper(),
            # BloomFieldHomesLakeBreezeNowScraper(),
            # UnionMainMyrtleCreekNowScraper(),
            # BloomFieldHomesMyrtleCreekNowScraper(),
            # HighlandHomesMyrtleCreekNowScraper(),
            # ChesmarHomesMyrtleCreekNowScraper(),
            # DavidWeekleyHomesMyrtleCreekNowScraper(),
            # UnionMainHomesReunionNowScraper(),
            # BeazerHomesReunionNowScraper(),
            # DRHortonBluestemNowScraper(),
            # UnionMainLakeBreezePlanScraper(),
            # BlueHavenHomesLakeBreezePlanScraper(),
            # UnionMainMyrtleCreekPlanScraper(),
            # HighlandHomesMyrtleCreekPlanScraper(),
            # ChesmarHomesMyrtleCreekPlanScraper(),
            # DavidWeekleyHomesMyrtleCreekPlanScraper(),
            # UnionMainHomesReunionPlanScraper(),
            # DRHortonReunionPlanScraper(),
            # BeazerHomesReunionPlanScraper(),
            # DRHortonBluestemPlanScraper(),
            # UnionMainPickensBluffNowScraper(),
            # DRHortonPickensBluffNowScraper(),
            # StarlightHomesPickensBluffNowScraper(),
            # PiedmontResidentialPickensBluffNowScraper(),
            # UnionMainPickensBluffPlanScraper(),
            # DRHortonPickensBluffPlanScraper(),
            # StarlightHomesPickensBluffPlanScraper(),
            # PiedmontResidentialPickensBluffPlanScraper(),
            # UnionMainWildflowerRanchPlanScraper(),
            # AmericanLegendHomesWildflowerRanchPlanScraper(),
            # DRHortonWildflowerRanchPlanScraper(),
            # DavidWeekleyHomesWildflowerRanchPlanScraper(),
            # PulteWildflowerRanchPlanScraper(),
            # MIHortonWildflowerRanchPlanScraper(),
            # AmericanLegendHomesWildflowerRanchNowScraper(),
            # DRHortonWildflowerRanchNowScraper(),
            # DavidWeekleyHomesWildflowerRanchNowScraper(),
            # PulteWildflowerRanchNowScraper(),
            # KBHomeWildflowerRanchNowScraper(),
            # MIHortonWildflowerRanchNowScraper(),
            # DavidsonHomesPickensBluffNowScraper(),
            # FischerHomesPickensBluffPlanScraper(),
            # FischerHomesPickensBluffNowScraper(),
            # FischerHomesLaurelFarmsPlanScraper(),
            # FischerHomesLaurelFarmsNowScraper(),
            # FischerHomesSageWoodsPlanScraper(),
            # FischerHomesSageWoodsNowScraper(),
            # BrightlandWaldenPondWestPlanScraper(),
            # UnionMainWaldenPondWestPlanScraper(),
            # PacesetterWaldenPondWestPlanScraper(),
            # CentexWaldenPondWestPlanScraper(),
            # HistoryMakerWaldenPondWestPlanScraper(),
            # BrightlandWaldenPondWestNowScraper(),
            # UnionMainWaldenPondWestNowScraper(),
            # PacesetterWaldenPondWestNowScraper(),
            # CentexWaldenPondWestNowScraper(),
            # HistoryMakerWaldenPondWestNowScraper(),
        ]
        self.timer = None
        self.running = False

    def start(self):
        self.running = True
        self.run()  # Run immediately on startup
        self.schedule_next_run()

    def stop(self):
        self.running = False
        if self.timer:
            self.timer.cancel()

    def schedule_next_run(self):
        if self.running:
            self.timer = threading.Timer(SCRAPE_INTERVAL_SECONDS, self.run)
            self.timer.start()

    def run(self):
        print("[Scheduler] Running all scrapers...")
        db = SessionLocal()
        try:
            for scraper in self.scrapers:
                print(f"[Scheduler] Running scraper: {scraper.__class__.__name__}")
                plans = scraper.fetch_plans()
                if plans:
                    detect_and_update_changes(db, plans)
                    print(f"[Scheduler] {scraper.__class__.__name__}: Updated {len(plans)} plans.")
                else:
                    print(f"[Scheduler] {scraper.__class__.__name__}: No plans found or scraping failed.")
        except Exception as e:
            print(f"[Scheduler] Error: {e}")
        finally:
            db.close()
        self.schedule_next_run()

scheduler = ScraperScheduler() 