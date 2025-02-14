using iHospitalUtility.Common.Constants;

namespace iHospitalUtility.Models
{
    public class CorrectedGestacionalAge
    {
        const int FullTermWeeks = 40;

        public int CorrectedWeeks { get; init; }
        public int CorrectedDays { get; init; }

        public string DisplayResult()
        {
            var isFullTerm = CorrectedWeeks >= FullTermWeeks;
            if (!isFullTerm)
                return $"{CorrectedWeeks} semanas e {CorrectedDays} dias";

            var weeksInDays = (CorrectedWeeks - FullTermWeeks) * TimeConstants.QtDiasSemana;
            var totalDaysAfterFullTerm = CorrectedDays + weeksInDays;
            return $"{FullTermWeeks} semanas a termo e {totalDaysAfterFullTerm} dias";
        }
    }
}
