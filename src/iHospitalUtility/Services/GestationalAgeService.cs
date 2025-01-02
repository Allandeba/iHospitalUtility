using iHospitalUtility.Models;
using iHospitalUtility.Services.Interfaces;

namespace iHospitalUtility.Services
{
    public class GestationalAgeService : IGestationalAgeService
    {
        private const int QtDiasSemana = 7;
        
        public CorrectedGestacionalAge GetCorrectAge(GestacionalAgeParams gestacionalAgeParams)
        {
            int totalDays = (gestacionalAgeParams.GestationalWeeks * QtDiasSemana) + gestacionalAgeParams.GestationalDays;
            DateTime today = DateTime.Now;
            int daysSinceBirth = (today - gestacionalAgeParams.BirthDate).Days;

            int correctedWeeks = (totalDays + daysSinceBirth) / QtDiasSemana;
            int correctedDays = (totalDays + daysSinceBirth) % QtDiasSemana;

            return new()
            {
                CorrectedWeeks = correctedWeeks,
                CorrectedDays = correctedDays,
            };
        }
    }
}