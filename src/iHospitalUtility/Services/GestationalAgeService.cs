using iHospitalUtility.Common.Constants;
using iHospitalUtility.Models;
using iHospitalUtility.Services.Interfaces;

namespace iHospitalUtility.Services
{
    public class GestationalAgeService : IGestationalAgeService
    {
        public CorrectedGestacionalAge GetCorrectAge(GestacionalAgeParams gestacionalAgeParams)
        {
            int totalDays = (gestacionalAgeParams.GestationalWeeks * TimeConstants.QtDiasSemana) + gestacionalAgeParams.GestationalDays;
            DateTime today = DateTime.Now;
            int daysSinceBirth = (today - gestacionalAgeParams.BirthDate).Days;

            int correctedWeeks = (totalDays + daysSinceBirth) / TimeConstants.QtDiasSemana;
            int correctedDays = (totalDays + daysSinceBirth) % TimeConstants.QtDiasSemana;

            return new()
            {
                CorrectedWeeks = correctedWeeks,
                CorrectedDays = correctedDays,
            };
        }
    }
}
