using iHospitalUtility.Models;

namespace iHospitalUtility.Services.Interfaces
{
    public interface IGestationalAgeService
    {
        CorrectedGestacionalAge GetCorrectAge(GestacionalAgeParams gestacionalAgeParams);
    }
}
