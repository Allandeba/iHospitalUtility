using Moq;
using iHospitalUtility.Models;
using iHospitalUtility.Services;

namespace iHospitalUtility_Test_Unit;

public class GestationalAgeTest
{
    private readonly GestationalAgeService _gestationalAgeService;
    public GestationalAgeTest()
    {
        _gestationalAgeService = new Mock<GestationalAgeService>().Object;
    }

    [Theory]
    [InlineData(9, 26, 1, 27, 3)]
    [InlineData(51, 29, 5, 37, 0)]
    [InlineData(59, 26, 1, 34, 4)]
    [InlineData(20, 25, 5, 28, 4)]
    [InlineData(47, 28, 1, 34, 6)]
    [InlineData(14, 27, 5, 29, 5)]
    public void ShouldReturnExactlyResult(
        int daysSinceBirth,
        int gestationalWeeks,
        int gestationalDays,
        int correctedWeeks,
        int correctedDays)
    {
        var birthDate = DateTime.Today.AddDays(-daysSinceBirth);
        var gestationalAgeParams = new GestacionalAgeParams()
        {
            GestationalWeeks = gestationalWeeks,
            GestationalDays = gestationalDays,
            BirthDate = birthDate,
        };

        var result = _gestationalAgeService.GetCorrectAge(gestationalAgeParams);
        Assert.Equal(correctedWeeks, result.CorrectedWeeks);
        Assert.Equal(correctedDays, result.CorrectedDays);
    }
}
